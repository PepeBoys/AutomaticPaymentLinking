"""Репозиторий для обработки входящих requestId вебхуков."""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WebhookRequest


class WebhookRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_request_id(self, request_id: str) -> Optional[WebhookRequest]:
        stmt = select(WebhookRequest).where(WebhookRequest.request_id == request_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_request_id(self, request_id: str) -> None:
        stmt = delete(WebhookRequest).where(WebhookRequest.request_id == request_id)
        await self._session.execute(stmt)

    async def cleanup_expired(self, now: datetime) -> None:
        stmt = delete(WebhookRequest).where(WebhookRequest.expires_at < now)
        await self._session.execute(stmt)

    async def save(
        self,
        *,
        request_id: str,
        account_id: str | None,
        events_count: int,
        status: str,
        expires_at: datetime,
    ) -> WebhookRequest:
        record = WebhookRequest(
            request_id=request_id,
            ms_account_id=account_id,
            events_count=events_count,
            status=status,
            expires_at=expires_at,
        )
        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise
        return record
