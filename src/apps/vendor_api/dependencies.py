from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.hooks.services.webhook_service import WebhookService
from src.apps.hooks.uow.unit_of_work import UnitOfWork
from src.apps.ms_auth.services.auth_service import (
    MySkladAuthService,
    get_ms_auth_service,
)
from src.core.database import get_session

from .services import VendorApiService


async def get_vendor_service(
    session: AsyncSession = Depends(get_session),
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> VendorApiService:
    webhook_service = WebhookService(
        uow=UnitOfWork(session), auth_service=auth_service
    )
    return VendorApiService(session=session, auth_service=auth_service, webhook_service=webhook_service)


AuthHeader = Annotated[str | None, Header(alias="Authorization")]
