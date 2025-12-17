"""Dependency Injection для расходных ордеров."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.cashout_service import CashOutService


async def get_cashout_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CashOutService:
    """Получить сервис расходных ордеров."""
    return CashOutService(auth_service=auth_service)


CashOutSvcDep = Annotated[CashOutService, Depends(get_cashout_service)]