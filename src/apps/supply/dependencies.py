"""Dependency Injection для отгрузок (supply)."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.services.auth_service import MySkladAuthService, get_ms_auth_service
from .services.supply_service import SupplyService


async def get_supply_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> SupplyService:
    """Получить сервис отгрузок (supply)."""

    return SupplyService(auth_service=auth_service)


SupplySvcDep = Annotated[SupplyService, Depends(get_supply_service)]