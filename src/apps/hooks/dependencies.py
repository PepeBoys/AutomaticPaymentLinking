from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.ms_auth.dependencies import get_ms_auth_service
from src.apps.ms_auth.services.auth_service import MySkladAuthService
from src.core.database import get_session

from .services.webhook_service import WebhookService
from .uow.unit_of_work import UnitOfWork
from .schemas import MySkladWebhookPayload


async def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)


async def set_request_account_from_webhook(
    payload: MySkladWebhookPayload, request: Request
) -> None:
    """Сохранить accountId из webhook payload в request.state.

    МойСклад всегда присылает accountId в событиях вебхука. Используем его
    как приоритетный источник контекста, чтобы обойтись без custom-заголовков
    при вызовах от самого МойСклад.
    """

    account_id = payload.events[0].accountId if payload.events else None
    if account_id:
        request.state.ms_account_id = account_id


async def get_webhook_service(
    uow: UnitOfWork = Depends(get_uow),
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> WebhookService:
    return WebhookService(uow=uow, auth_service=auth_service)


UOWDep = Annotated[UnitOfWork, Depends(get_uow)]
WebhookSvcDep = Annotated[WebhookService, Depends(get_webhook_service)]
RequestIdQuery = Annotated[str | None, Query(alias="requestId")]