"""Репозиторий соответствий статья расходов ↔ элемент справочника-зеркала."""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.entities import ExpenseItemMappingEntity
from ..exceptions import ExpenseSyncRepositoryError
from ..models import ExpenseItemMapping

logger = logging.getLogger(__name__)


class ExpenseItemMappingRepository:
    """Доступ к таблице соответствий expenseitem ↔ элемент customentity."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_account(self, account_id: str) -> List[ExpenseItemMappingEntity]:
        stmt = select(ExpenseItemMapping).where(
            ExpenseItemMapping.ms_account_id == account_id
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_by_expenseitem(
        self, account_id: str, expenseitem_id: str
    ) -> Optional[ExpenseItemMappingEntity]:
        stmt = select(ExpenseItemMapping).where(
            ExpenseItemMapping.ms_account_id == account_id,
            ExpenseItemMapping.expenseitem_id == expenseitem_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_element(
        self, account_id: str, customentity_element_id: str
    ) -> Optional[ExpenseItemMappingEntity]:
        stmt = select(ExpenseItemMapping).where(
            ExpenseItemMapping.ms_account_id == account_id,
            ExpenseItemMapping.customentity_element_id == customentity_element_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add(
        self, account_id: str, expenseitem_id: str, customentity_element_id: str
    ) -> ExpenseItemMappingEntity:
        if not account_id or not account_id.strip():
            raise ExpenseSyncRepositoryError("ms_account_id is required")

        model = ExpenseItemMapping(
            ms_account_id=account_id,
            expenseitem_id=expenseitem_id,
            customentity_element_id=customentity_element_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete_by_expenseitem(self, account_id: str, expenseitem_id: str) -> bool:
        stmt = select(ExpenseItemMapping).where(
            ExpenseItemMapping.ms_account_id == account_id,
            ExpenseItemMapping.expenseitem_id == expenseitem_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def delete_by_element(
        self, account_id: str, customentity_element_id: str
    ) -> bool:
        stmt = select(ExpenseItemMapping).where(
            ExpenseItemMapping.ms_account_id == account_id,
            ExpenseItemMapping.customentity_element_id == customentity_element_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_entity(model: ExpenseItemMapping) -> ExpenseItemMappingEntity:
        return ExpenseItemMappingEntity(
            id=model.id,
            ms_account_id=model.ms_account_id,
            expenseitem_id=model.expenseitem_id,
            customentity_element_id=model.customentity_element_id,
        )
