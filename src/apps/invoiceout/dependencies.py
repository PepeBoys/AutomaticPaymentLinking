"""Dependency Injection для счетов покупателю."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.invoiceout_service import InvoiceOutService


async def get_invoiceout_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> InvoiceOutService:
    """Получить сервис счетов покупателю."""
    return InvoiceOutService(auth_service=auth_service)


InvoiceOutSvcDep = Annotated[InvoiceOutService, Depends(get_invoiceout_service)]