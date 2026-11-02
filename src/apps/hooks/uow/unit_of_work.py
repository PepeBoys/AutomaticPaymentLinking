"""Unit of Work для управления транзакциями."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.webhook_repository import WebhookRepository


class UnitOfWork:
    """
    Unit of Work для управления транзакциями и репозиториями.
    
    Обеспечивает:
    - Единую точку входа для работы с репозиториями
    - Управление транзакциями
    - Автоматический commit/rollback
    """
    
    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализировать Unit of Work.
        
        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self._session = session
        self._webhooks: Optional[WebhookRepository] = None
        self._committed = False
    
    @property
    def webhooks(self) -> WebhookRepository:
        """
        Получить репозиторий вебхуков.
        
        Returns:
            Репозиторий вебхуков
        """
        if self._webhooks is None:
            self._webhooks = WebhookRepository(self._session)
        return self._webhooks

    @property
    def session(self) -> AsyncSession:
        """Сессия для запросов за пределами репозиториев модуля."""
        return self._session

    async def commit(self) -> None:
        """Зафиксировать изменения в БД."""
        self._committed = True
        await self._session.commit()
    
    async def rollback(self) -> None:
        """Откатить изменения."""
        await self._session.rollback()
    
    async def __aenter__(self) -> "UnitOfWork":
        """Вход в контекстный менеджер."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Выход из контекстного менеджера.
        
        Автоматически откатывает транзакцию при исключении.
        """
        if exc_type is not None:
            await self.rollback()