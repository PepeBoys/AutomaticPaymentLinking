"""Dependency Injection для приходных ордеров."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.services.auth_service import MySkladAuthService, get_ms_auth_service
from .services.cashout_service import CashOutService


async def get_cashout_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CashOutService:
    """Получить сервис приходных ордеров."""
    return CashOutService(auth_service=auth_service)


CashOutSvcDep = Annotated[CashOutService, Depends(get_cashout_service)]