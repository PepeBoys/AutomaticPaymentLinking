"""Dependency Injection для отгрузок (demand)."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.demand_service import DemandService


async def get_demand_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> DemandService:
    """Получить сервис отгрузок (demand)."""

    return DemandService(auth_service=auth_service)


DemandSvcDep = Annotated[DemandService, Depends(get_demand_service)]