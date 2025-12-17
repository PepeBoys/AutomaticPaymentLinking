from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.ms_auth.dependencies import get_ms_auth_service
from src.apps.ms_auth.services.auth_service import MySkladAuthService
from src.core.database import get_session

from .services.webhook_service import WebhookService
from .uow.unit_of_work import UnitOfWork


async def get_uow(session: AsyncSession = Depends(get_session)) -> UnitOfWork:
    return UnitOfWork(session)


async def get_webhook_service(
    uow: UnitOfWork = Depends(get_uow),
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> WebhookService:
    return WebhookService(uow=uow, auth_service=auth_service)


UOWDep = Annotated[UnitOfWork, Depends(get_uow)]
WebhookSvcDep = Annotated[WebhookService, Depends(get_webhook_service)]
RequestIdQuery = Annotated[str | None, Query(alias="requestId")]