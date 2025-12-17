"""Dependency Injection для входящих платежей."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.paymentout_service import PaymentOutService


async def get_paymentout_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> PaymentOutService:
    """Получить сервис входящих платежей."""
    return PaymentOutService(auth_service=auth_service)


PaymentOutSvcDep = Annotated[PaymentOutService, Depends(get_paymentout_service)]