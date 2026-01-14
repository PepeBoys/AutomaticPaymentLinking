import logging
from typing import Callable

import httpx
from fastapi import Request, Response
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.database import async_session_maker

from .models import VendorAccount
from .security import create_vendor_jwt

logger = logging.getLogger(__name__)


class AppUidAccountMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического определения account_id через contextKey.

    Алгоритм:
    1. При первой загрузке iframe (есть contextKey) → запрос к Vendor API → accountId → cookie
    2. При последующих запросах (нет contextKey) → чтение из cookie
    """

    COOKIE_NAME = "ms_account_id"
    COOKIE_MAX_AGE = 86400  # 24 часа
    VENDOR_API_BASE = "https://apps-api.moysklad.ru/api/vendor/1.0"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Для отладки и проверки теории фикса бага.
        logger.info(
            "=== INCOMING REQUEST === path=%s, query_params=%s",
            request.url.path,
            dict(request.query_params),
        )
        # Если account_id уже установлен (например, из вебхука) - пропускаем
        if hasattr(request.state, "ms_account_id") and request.state.ms_account_id:
            logger.debug("Account ID уже установлен: %s", request.state.ms_account_id)
            return await call_next(request)

        account_id = None
        context_key = None

        # 1. Если есть contextKey - получаем accountId через Vendor API
        context_key = request.query_params.get("contextKey")
        if context_key:
            account_id = await self._get_account_id_via_vendor_api(context_key)
            if account_id:
                logger.info(
                    "Account ID получен через Vendor API (contextKey=%s...): %s",
                    context_key[:20],
                    account_id,
                )

        # 2. Если contextKey нет - читаем из cookie
        if not account_id:
            account_id = request.cookies.get(self.COOKIE_NAME)
            if account_id:
                logger.debug("Account ID прочитан из cookie: %s", account_id)

        # 3. Проверяем валидность account_id в БД
        if account_id:
            is_valid = await self._validate_account(account_id)
            if not is_valid:
                logger.warning(
                    "Account ID %s не найден или неактивен в БД, сброс",
                    account_id,
                )
                account_id = None

        # 4. Устанавливаем в request.state
        if account_id:
            request.state.ms_account_id = account_id

        # Выполняем запрос
        response = await call_next(request)

        # 5. Если получили accountId через contextKey - сохраняем в cookie
        if context_key and account_id and isinstance(response, Response):
            response.set_cookie(
                key=self.COOKIE_NAME,
                value=account_id,
                max_age=self.COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )
            logger.info("Account ID сохранен в cookie: %s", account_id)

        return response

    async def _get_account_id_via_vendor_api(self, context_key: str) -> str | None:
        """
        Получить accountId через Vendor API по contextKey.

        GET /context/{contextKey} -> {"accountId": "...", "userId": "...", ...}
        """
        try:
            jwt_token = create_vendor_jwt()
            headers = {"Authorization": f"Bearer {jwt_token}"}
            url = f"{self.VENDOR_API_BASE}/context/{context_key}"

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                account_id = data.get("accountId")

                if account_id:
                    logger.info(
                        "Vendor API context успешно получен: accountId=%s, userId=%s, isAdmin=%s",
                        account_id,
                        data.get("userId"),
                        data.get("isAdmin"),
                    )
                    return account_id

                logger.warning("Vendor API context не вернул accountId")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(
                "Vendor API HTTP error (contextKey=%s...): %s %s",
                context_key[:20],
                e.response.status_code,
                e.response.text,
            )
            return None
        except Exception as e:
            logger.error(
                "Ошибка при запросе к Vendor API (contextKey=%s...): %s",
                context_key[:20],
                e,
                exc_info=True,
            )
            return None

    async def _validate_account(self, account_id: str) -> bool:
        """Проверить, что аккаунт существует и активен в БД."""
        try:
            async with async_session_maker() as session:
                stmt = (
                    select(VendorAccount.account_id)
                    .where(VendorAccount.account_id == account_id)
                    .where(VendorAccount.is_active.is_(True))
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(
                "Ошибка при проверке account_id=%s: %s",
                account_id,
                e,
                exc_info=True,
            )
            return False