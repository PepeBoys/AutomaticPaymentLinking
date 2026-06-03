"""Управление настройками фичи синхронизации статей расходов."""

import logging

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import ExpenseSyncBaseException
from ..uow.unit_of_work import ExpenseSyncUnitOfWork

logger = logging.getLogger(__name__)


class ExpenseSyncService:
    """Статус и переключение фичи автопроставления статьи расходов."""

    def __init__(
        self, auth_service: MySkladAuthService, uow: ExpenseSyncUnitOfWork
    ) -> None:
        self._auth_service = auth_service
        self._uow = uow

    def _require_account_id(self) -> str:
        account_id = self._auth_service.get_account_id()
        if not account_id:
            raise ExpenseSyncBaseException(
                "AccountId не найден. Активируйте приложение через Vendor API"
            )
        return account_id

    async def get_status(self) -> dict:
        """Текущее состояние фичи для аккаунта."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if config is None:
            return {
                "enabled": False,
                "initialized": False,
                "mirror_customentity_id": None,
                "counterparty_attribute_id": None,
                "mappings_count": 0,
            }

        mappings = await self._uow.mappings.list_by_account(account_id)
        return {
            "enabled": config.enabled,
            "initialized": config.is_initialized,
            "mirror_customentity_id": config.mirror_customentity_id,
            "counterparty_attribute_id": config.counterparty_attribute_id,
            "mappings_count": len(mappings),
        }

    async def set_enabled(self, enabled: bool) -> dict:
        """Включить/выключить автопроставление статьи расходов."""
        account_id = self._require_account_id()
        config = await self._uow.configs.get_by_account_id(account_id)

        if enabled and (config is None or not config.is_initialized):
            return {
                "status": "warning",
                "enabled": False,
                "message": (
                    "Инфраструктура не инициализирована. Сначала выполните "
                    "инициализацию справочника статей расходов."
                ),
            }

        await self._uow.configs.upsert(account_id, enabled=enabled)
        await self._uow.commit()

        logger.info(
            "Фича статьи расходов переключена: account_id=%s, enabled=%s",
            account_id,
            enabled,
        )
        return {"status": "ok", "enabled": enabled}
