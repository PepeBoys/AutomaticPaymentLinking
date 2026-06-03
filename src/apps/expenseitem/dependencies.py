"""Dependency Injection для статей расходов."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.expenseitem_service import ExpenseItemService


async def get_expenseitem_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> ExpenseItemService:
    """Получить сервис статей расходов."""
    return ExpenseItemService(auth_service=auth_service)


ExpenseItemSvcDep = Annotated[ExpenseItemService, Depends(get_expenseitem_service)]
