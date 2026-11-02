"""Статус и переключение фичи автопроставления статьи доходов."""

import logging

from src.core.config import settings

from ...cashin.services.cashin_service import CashInService
from ...counterparty.exceptions import CounterpartyAPIError
from ...counterparty.services.counterparty_service import CounterpartyService
from ...customentity.exceptions import (
    CustomEntityAPIError,
    CustomEntityNotFoundError,
)
from ...customentity.services.customentity_service import CustomEntityService
from ...ms_auth.services.auth_service import MySkladAuthService
from ...payment_base.exceptions import PaymentAPIError
from ...paymentin.services.paymentin_service import PaymentInService
from ..constants import INCOME_PAYMENT_ENTITY_TYPES, INCOME_PAYMENT_WEBHOOK_ACTION
from ..domain.entities import ATTRIBUTE_FIELDS
from ..exceptions import IncomeSyncBaseException
from ..uow.unit_of_work import IncomeSyncUnitOfWork

logger = logging.getLogger(__name__)


class IncomeSyncService:
    """Статус и переключение фичи автопроставления статьи доходов."""

    def __init__(
        self,
        auth_service: MySkladAuthService,
        uow: IncomeSyncUnitOfWork,
        customentity_service: CustomEntityService,
        counterparty_service: CounterpartyService,
        paymentin_service: PaymentInService,
        cashin_service: CashInService,
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow
        self._customentity_service = customentity_service
        self._attribute_owners = {
            "counterparty_attribute_id": counterparty_service,
            "paymentin_attribute_id": paymentin_service,
            "cashin_attribute_id": cashin_service,
        }

    # Тексты диагностики для UI: почему инфраструктура считается неготовой.
    _DIAGNOSTIC_MESSAGES = {
        "dictionary_missing": (
            "Справочник «Статьи доходов» не найден в МойСклад (вместе с ним "
            "удалены и доп. поля). Требуется повторная инициализация."
        ),
        "attribute_missing": (
            "Одно из доп. полей статьи доходов не найдено в МойСклад. "
            "Требуется повторная инициализация."
        ),
    }

    @classmethod
    def _uninitialized_status(cls, diagnostic: str = "none") -> dict:
        return {
            "enabled": False,
            "initialized": False,
            "dictionary_id": None,
            "counterparty_attribute_id": None,
            "paymentin_attribute_id": None,
            "cashin_attribute_id": None,
            "diagnostic": diagnostic,
            "message": cls._DIAGNOSTIC_MESSAGES.get(diagnostic),
        }

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise IncomeSyncBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def _dictionary_exists(self, dictionary_id: str) -> bool:
        """Жив ли справочник в МойСклад.

        404 — справочник удалён. При сетевой/прочей ошибке считаем его
        существующим, чтобы транзиентный сбой не уничтожил конфиг.
        """
        try:
            await self._customentity_service.get_metadata(dictionary_id)
            return True
        except CustomEntityNotFoundError:
            return False
        except CustomEntityAPIError as exc:
            logger.warning(
                "Не удалось проверить справочник статей доходов %s, считаем существующим: %s",
                dictionary_id,
                exc,
            )
            return True

    async def _attribute_exists(self, field_name: str, attribute_id: str) -> bool:
        """Живо ли доп. поле в МойСклад (при сбое — считаем существующим)."""
        try:
            return await self._attribute_owners[field_name].attribute_exists(attribute_id)
        except (CounterpartyAPIError, PaymentAPIError) as exc:
            logger.warning(
                "Не удалось проверить доп. поле %s=%s, считаем существующим: %s",
                field_name,
                attribute_id,
                exc,
            )
            return True

    async def get_status(self) -> dict:
        """Текущее состояние фичи для аккаунта."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if config is None:
            return self._uninitialized_status()

        # Самовосстановление: справочник удалён в МС — сохранённые id
        # «призрачные», чистим конфиг, чтобы UI предложил инициализацию заново.
        if config.dictionary_id and not await self._dictionary_exists(
            config.dictionary_id
        ):
            await self._uow.configs.delete_by_account_id(account_id)
            await self._uow.commit()
            logger.info(
                "Сброшен конфиг income_sync (справочник удалён в МС): account_id=%s",
                account_id,
            )
            return self._uninitialized_status("dictionary_missing")

        # Удалено отдельное доп. поле — сбрасываем ссылку на него, повторная
        # инициализация пересоздаст поле на существующем справочнике.
        for field_name in ATTRIBUTE_FIELDS:
            attribute_id = getattr(config, field_name)
            if attribute_id and not await self._attribute_exists(field_name, attribute_id):
                await self._uow.configs.clear_attribute(account_id, field_name)
                await self._uow.commit()
                logger.info(
                    "Сброшена ссылка на удалённое доп. поле %s: account_id=%s",
                    field_name,
                    account_id,
                )
                return self._uninitialized_status("attribute_missing")

        if not config.is_initialized:
            diagnostic = "attribute_missing" if config.dictionary_id else "none"
            return self._uninitialized_status(diagnostic)

        return {
            "enabled": config.enabled,
            "initialized": True,
            "dictionary_id": config.dictionary_id,
            "counterparty_attribute_id": config.counterparty_attribute_id,
            "paymentin_attribute_id": config.paymentin_attribute_id,
            "cashin_attribute_id": config.cashin_attribute_id,
            "diagnostic": "ok",
            "message": None,
        }

    async def set_enabled(self, enabled: bool) -> dict:
        """Включить/выключить автопроставление статьи доходов."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if enabled and (config is None or not config.is_initialized):
            return {
                "status": "warning",
                "enabled": False,
                "message": (
                    "Инфраструктура не инициализирована. Сначала выполните "
                    "инициализацию справочника статей доходов."
                ),
            }

        await self._uow.configs.upsert(account_id, enabled=enabled)
        await self._uow.commit()

        logger.info(
            "Фича статьи доходов переключена: account_id=%s, enabled=%s",
            account_id,
            enabled,
        )

        if enabled:
            errors = await self._ensure_payment_webhooks_enabled()
            if errors:
                return {"status": "warning", "enabled": True, "message": "; ".join(errors)}

        return {"status": "ok", "enabled": enabled}

    async def _ensure_payment_webhooks_enabled(self) -> list[str]:
        """Включить вебхуки paymentin/cashin CREATE, если автопривязка их выключила."""
        webhook_url = settings.ms_webhook_url
        if not webhook_url:
            logger.warning("MS_WEBHOOK_URL не задан, вебхуки статьи доходов не проверены")
            return ["MS_WEBHOOK_URL не задан — вебхуки не проверены"]

        # Локальный импорт во избежание циклической зависимости hooks <-> income_sync.
        from ...hooks.services.moysklad_client import MoySkladClient
        from ...hooks.services.shared_webhooks import ensure_webhooks_enabled

        ensured = await ensure_webhooks_enabled(
            MoySkladClient(self._auth_service),
            webhook_url,
            [
                (entity_type, INCOME_PAYMENT_WEBHOOK_ACTION)
                for entity_type in INCOME_PAYMENT_ENTITY_TYPES
            ],
        )
        return ensured.errors
