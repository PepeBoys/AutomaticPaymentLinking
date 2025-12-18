import logging
from datetime import UTC, datetime
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.hooks.schemas import PaymentType
from src.apps.hooks.services.webhook_service import WebhookService
from src.apps.hooks.uow.unit_of_work import UnitOfWork
from src.apps.ms_auth.services.auth_service import MySkladAuthService
from src.core.config import settings

from .repository import VendorAccountRepository, VendorJtiRepository
from .schemas import ActivationPayload, ActivationResponse
from .security import JwtVerificationError, verify_vendor_jwt

logger = logging.getLogger(__name__)


class VendorApiService:
    def __init__(
        self,
        session: AsyncSession,
        auth_service: MySkladAuthService,
        webhook_service: WebhookService,
    ) -> None:
        self._session = session
        self._auth_service = auth_service
        self._webhook_service = webhook_service
        self._accounts = VendorAccountRepository(session)
        self._jtis = VendorJtiRepository(session)
        self._uow = UnitOfWork(session)

    async def activate_app(
        self, app_id: str, account_id: str, payload: ActivationPayload, jwt_token: str
    ) -> ActivationResponse:
        logger.info(
            "=== НАЧАЛО АКТИВАЦИИ === account_id=%s, jti=%s",
            account_id,
            jwt_token[-20:] if jwt_token else "N/A",
        )
        # 1) validate request meta
        self._validate_app_id(app_id)
        self._validate_app_uid(payload.appUid)

        # 2) verify JWT + replay guard
        claims = self._verify_jwt(jwt_token)
        await self._guard_replay(claims)

        logger.info(
            "JWT проверен, jti=%s сохранён в БД (защита от повторов)",
            claims.get("jti"),
        )

        # 3) get remap token (issued by MS) + base_url
        access_token, base_url = self._extract_access_token_and_base_url(payload)

        # Проверяем был ли аккаунт активен ДО обновления
        existing_account = await self._accounts.get_by_account_id(account_id)
        was_active = existing_account and existing_account.is_active
        
        if was_active:
            logger.info(
                "Аккаунт уже был активен (повторный запрос активации от МС). Пропускаем очистку вебхуков."
            )
        else:
            logger.info("Аккаунт неактивен или новый. Будет выполнена очистка вебхуков.")


        # 4) persist account linkage
        await self._accounts.upsert_account(
            account_id=account_id,
            access_token=access_token,
            base_url=base_url,
            app_uid=settings.ms_app_uid,
        )

        # 5) configure MS auth for this request context
        self._auth_service.set_access_token(
            access_token, base_url=base_url, account_id=account_id
        )

        # 5) cleanup old webhooks ТОЛЬКО если это реальная переустановка (аккаунт был неактивен)
        if not was_active:
            cleanup_stats = await self._webhook_service.cleanup_account_webhooks(account_id)
            logger.info(
                "Очистка вебхуков перед активацией account_id=%s: "
                "deleted_from_ms=%d, not_found_in_ms=%d, failed_to_delete_from_ms=%d, deleted_from_db=%d",
                account_id,
                cleanup_stats["deleted_from_ms"],
                cleanup_stats["not_found_in_ms"],
                cleanup_stats["failed_to_delete_from_ms"],
                cleanup_stats["deleted_from_db"],
            )
            await self._session.commit()
            self._session.expire_all()
            logger.info("Изменения после очистки вебхуков зафиксированы")
        else:
            logger.info(
                "Пропуск очистки вебхуков (аккаунт уже активен). "
                "Существующие вебхуки будут проверены и переиспользованы. "
                "Если URL изменился - он будет обновлён."
            )

        # 6) enable required webhooks in MS
        logger.info("Создание вебхуков для account_id=%s", account_id)
        for payment_type in self._default_payment_types():
            result = await self._webhook_service.toggle_webhook(
                payment_type=payment_type, 
                enabled=True,
                # skip_existing_db_check=True,
            )
            logger.info("Webhook %s: operation=%s, success=%s", payment_type.value, result.operation, result.success)
        

        await self._session.commit()

        logger.info(
            "=== КОНЕЦ АКТИВАЦИИ === "
            "Vendor app activated: account_id=%s, app_uid=%s, jti=%s",
            account_id,
            payload.appUid,
            claims.get("jti"),
        )
        return ActivationResponse(status="Activated")

    async def deactivate_app(self, app_id: str, account_id: str, jwt_token: str) -> None:
        self._validate_app_id(app_id)
        claims = self._verify_jwt(jwt_token)
        await self._guard_replay(claims)

        logger.info(
            "Деактивация: очистка только БД (токен отозван МС до вызова DELETE). "
            "Вебхуки останутся в МС и будут переиспользованы при следующей активации."
        )
        
        deleted_count = await self._uow.webhooks.delete_all_by_account_id(account_id)
        logger.info(
            "Удалено записей из БД при деактивации: %d для account_id=%s",
            deleted_count,
            account_id,
        )

        await self._accounts.deactivate_account(account_id)
        self._auth_service.clear_access_token()
        await self._session.commit()

        logger.info(
            "Vendor app deactivated: account_id=%s, jti=%s", account_id, claims.get("jti")
        )

    @staticmethod
    def _default_payment_types() -> Iterable[PaymentType]:
        return [
            PaymentType.incoming_payment,
            PaymentType.incoming_order,
            PaymentType.outgoing_payment,
            PaymentType.outgoing_order,
        ]

    def _validate_app_id(self, app_id: str) -> None:
        if app_id != settings.ms_app_id:
            logger.warning("Invalid app_id in vendor request: %s", app_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid appId",
            )

    def _validate_app_uid(self, app_uid: str) -> None:
        if app_uid != settings.ms_app_uid:
            logger.warning("Invalid app_uid in vendor request: %s", app_uid)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid appUid",
            )

    def _verify_jwt(self, token: str) -> dict:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Authorization token",
            )
        try:
            return verify_vendor_jwt(token)
        except JwtVerificationError as exc:
            logger.warning("JWT verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            ) from exc

    async def _guard_replay(self, claims: dict) -> None:
        jti = claims.get("jti")
        exp = claims.get("exp")
        if not jti or not exp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed token",
            )

        await self._jtis.cleanup_expired(datetime.now(UTC))

        if await self._jtis.is_used(jti):
            logger.warning("Replay attempt detected: jti=%s", jti)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Token has already been used",
            )

        expires_at = datetime.fromtimestamp(exp, tz=UTC)
        await self._jtis.save(jti=jti, expires_at=expires_at)

    def _extract_access_token_and_base_url(self, payload: ActivationPayload) -> tuple[str, str]:
        """
        Vendor API activation payload contains access_token inside access[] items.
        We pick the first item where access_token is present.

        base_url:
          - Prefer resource from access[] (often ends with /api/remap/1.2 or /api/remap/1.2/)
          - Fallback to settings.ms_base_url
        """
        for a in payload.access:
            if a.access_token:
                base_url = (a.resource or settings.ms_base_url).rstrip("/")
                return a.access_token, base_url

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing access_token in payload.access[]",
        )
