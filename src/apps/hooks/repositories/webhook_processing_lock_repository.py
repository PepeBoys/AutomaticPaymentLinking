"""Репозиторий блокировок обработки вебхуков."""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WebhookProcessingLock


class WebhookProcessingLockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_account_id(
        self, account_id: str
    ) -> Optional[WebhookProcessingLock]:
        stmt = select(WebhookProcessingLock).where(
            WebhookProcessingLock.account_id == account_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_account_id(self, account_id: str) -> None:
        stmt = delete(WebhookProcessingLock).where(
            WebhookProcessingLock.account_id == account_id
        )
        await self._session.execute(stmt)

    async def cleanup_expired(self, now: datetime) -> None:
        stmt = delete(WebhookProcessingLock).where(
            WebhookProcessingLock.expires_at < now
        )
        await self._session.execute(stmt)

    async def acquire(self, *, account_id: str, expires_at: datetime) -> bool:
        record = WebhookProcessingLock(
            account_id=account_id,
            expires_at=expires_at,
        )
        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True
