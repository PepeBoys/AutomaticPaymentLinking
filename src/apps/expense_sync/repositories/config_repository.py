"""Репозиторий настроек фичи синхронизации статей расходов."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.entities import ExpenseSyncConfig
from ..exceptions import ExpenseSyncRepositoryError
from ..models import ExpenseItemSyncConfig

logger = logging.getLogger(__name__)


class ExpenseSyncConfigRepository:
    """Доступ к настройкам фичи (одна запись на аккаунт)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(self, account_id: str) -> Optional[ExpenseSyncConfig]:
        stmt = select(ExpenseItemSyncConfig).where(
            ExpenseItemSyncConfig.ms_account_id == account_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(
        self,
        account_id: str,
        *,
        mirror_customentity_id: Optional[str] = None,
        counterparty_attribute_id: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> ExpenseSyncConfig:
        """Создать или частично обновить настройки аккаунта.

        Передаются только те поля, что нужно изменить; None означает «не
        трогать» (кроме создания новой записи, где применяются значения по
        умолчанию).
        """
        if not account_id or not account_id.strip():
            raise ExpenseSyncRepositoryError("ms_account_id is required")

        stmt = select(ExpenseItemSyncConfig).where(
            ExpenseItemSyncConfig.ms_account_id == account_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = ExpenseItemSyncConfig(
                ms_account_id=account_id,
                mirror_customentity_id=mirror_customentity_id,
                counterparty_attribute_id=counterparty_attribute_id,
                enabled=bool(enabled) if enabled is not None else False,
            )
            self._session.add(model)
        else:
            if mirror_customentity_id is not None:
                model.mirror_customentity_id = mirror_customentity_id
            if counterparty_attribute_id is not None:
                model.counterparty_attribute_id = counterparty_attribute_id
            if enabled is not None:
                model.enabled = enabled

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: ExpenseItemSyncConfig) -> ExpenseSyncConfig:
        return ExpenseSyncConfig(
            id=model.id,
            ms_account_id=model.ms_account_id,
            mirror_customentity_id=model.mirror_customentity_id,
            counterparty_attribute_id=model.counterparty_attribute_id,
            enabled=model.enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
