"""Dependency Injection для заказов покупателя."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.customerorder_service import CustomerOrderService


async def get_customerorder_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CustomerOrderService:
    """
    Получить сервис заказов покупателя.
    
    Args:
        auth_service: Сервис аутентификации
        
    Returns:
        Сервис заказов покупателя
    """
    return CustomerOrderService(auth_service=auth_service)


CustomerOrderSvcDep = Annotated[
    CustomerOrderService,
    Depends(get_customerorder_service)
]