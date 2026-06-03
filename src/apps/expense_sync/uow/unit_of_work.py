"""Unit of Work для модуля синхронизации статей расходов."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.config_repository import ExpenseSyncConfigRepository
from ..repositories.mapping_repository import ExpenseItemMappingRepository


class ExpenseSyncUnitOfWork:
    """Управление транзакциями и репозиториями модуля expense_sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._configs: Optional[ExpenseSyncConfigRepository] = None
        self._mappings: Optional[ExpenseItemMappingRepository] = None
        self._committed = False

    @property
    def configs(self) -> ExpenseSyncConfigRepository:
        if self._configs is None:
            self._configs = ExpenseSyncConfigRepository(self._session)
        return self._configs

    @property
    def mappings(self) -> ExpenseItemMappingRepository:
        if self._mappings is None:
            self._mappings = ExpenseItemMappingRepository(self._session)
        return self._mappings

    async def commit(self) -> None:
        self._committed = True
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> "ExpenseSyncUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
