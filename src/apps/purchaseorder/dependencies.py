"""Dependency Injection для заказов покупателя."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.purchaseorder_service import PurchaseOrderService


async def get_purchaseorder_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> PurchaseOrderService:
    """
    Получить сервис заказов покупателя.
    
    Args:
        auth_service: Сервис аутентификации
        
    Returns:
        Сервис заказов покупателя
    """
    return PurchaseOrderService(auth_service=auth_service)


PurchaseOrderSvcDep = Annotated[
    PurchaseOrderService,
    Depends(get_purchaseorder_service)
]