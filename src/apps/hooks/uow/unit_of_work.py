"""Unit of Work для управления транзакциями."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.webhook_processing_lock_repository import (
    WebhookProcessingLockRepository,
)
from ..repositories.webhook_repository import WebhookRepository
from ..repositories.webhook_request_repository import WebhookRequestRepository


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
        self._webhook_requests: Optional[WebhookRequestRepository] = None
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
    def webhook_requests(self) -> WebhookRequestRepository:
        if self._webhook_requests is None:
            self._webhook_requests = WebhookRequestRepository(self._session)
        return self._webhook_requests
    
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
