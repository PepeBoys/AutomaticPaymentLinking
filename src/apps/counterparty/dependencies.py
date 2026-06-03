"""Dependency Injection для контрагентов."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.counterparty_service import CounterpartyService


async def get_counterparty_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CounterpartyService:
    """Получить сервис контрагентов."""
    return CounterpartyService(auth_service=auth_service)


CounterpartySvcDep = Annotated[CounterpartyService, Depends(get_counterparty_service)]
