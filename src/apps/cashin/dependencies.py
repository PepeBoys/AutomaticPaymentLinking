"""Dependency Injection для приходных ордеров."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.cashin_service import CashInService


async def get_cashin_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CashInService:
    """Получить сервис приходных ордеров."""
    return CashInService(auth_service=auth_service)


CashInSvcDep = Annotated[CashInService, Depends(get_cashin_service)]