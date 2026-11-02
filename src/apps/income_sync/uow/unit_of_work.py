"""Unit of Work для модуля автопроставления статьи доходов."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.config_repository import IncomeSyncConfigRepository


class IncomeSyncUnitOfWork:
    """Управление транзакциями и репозиториями модуля income_sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._configs: Optional[IncomeSyncConfigRepository] = None
        self._committed = False

    @property
    def configs(self) -> IncomeSyncConfigRepository:
        if self._configs is None:
            self._configs = IncomeSyncConfigRepository(self._session)
        return self._configs

    async def commit(self) -> None:
        self._committed = True
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> "IncomeSyncUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            await self.rollback()
