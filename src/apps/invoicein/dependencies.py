"""Dependency Injection для счетов покупателю."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.invoicein_service import InvoiceInService


async def get_invoicein_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> InvoiceInService:
    """Получить сервис счетов покупателю."""
    return InvoiceInService(auth_service=auth_service)


InvoiceInSvcDep = Annotated[InvoiceInService, Depends(get_invoicein_service)]