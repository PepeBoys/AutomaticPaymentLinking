"""Dependency Injection для модуля синхронизации статей расходов."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

from ..counterparty.dependencies import get_counterparty_service
from ..counterparty.services.counterparty_service import CounterpartyService
from ..customentity.dependencies import get_customentity_service
from ..customentity.services.customentity_service import CustomEntityService
from ..expenseitem.dependencies import get_expenseitem_service
from ..expenseitem.services.expenseitem_service import ExpenseItemService
from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.expense_sync_service import ExpenseSyncService
from .services.setup_service import ExpenseItemSetupService
from .services.sync_service import ExpenseSyncHandler
from .uow.unit_of_work import ExpenseSyncUnitOfWork


async def get_expense_sync_uow(
    session: AsyncSession = Depends(get_session),
) -> ExpenseSyncUnitOfWork:
    return ExpenseSyncUnitOfWork(session)


ExpenseSyncUOWDep = Annotated[ExpenseSyncUnitOfWork, Depends(get_expense_sync_uow)]


async def get_expense_setup_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: ExpenseSyncUnitOfWork = Depends(get_expense_sync_uow),
    expenseitem_service: ExpenseItemService = Depends(get_expenseitem_service),
    customentity_service: CustomEntityService = Depends(get_customentity_service),
    counterparty_service: CounterpartyService = Depends(get_counterparty_service),
) -> ExpenseItemSetupService:
    return ExpenseItemSetupService(
        auth_service=auth_service,
        uow=uow,
        expenseitem_service=expenseitem_service,
        customentity_service=customentity_service,
        counterparty_service=counterparty_service,
    )


ExpenseSetupSvcDep = Annotated[
    ExpenseItemSetupService, Depends(get_expense_setup_service)
]


async def get_expense_sync_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: ExpenseSyncUnitOfWork = Depends(get_expense_sync_uow),
) -> ExpenseSyncService:
    return ExpenseSyncService(auth_service=auth_service, uow=uow)


ExpenseSyncSvcDep = Annotated[ExpenseSyncService, Depends(get_expense_sync_service)]


async def get_expense_sync_handler(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: ExpenseSyncUnitOfWork = Depends(get_expense_sync_uow),
    expenseitem_service: ExpenseItemService = Depends(get_expenseitem_service),
    customentity_service: CustomEntityService = Depends(get_customentity_service),
    counterparty_service: CounterpartyService = Depends(get_counterparty_service),
) -> ExpenseSyncHandler:
    return ExpenseSyncHandler(
        auth_service=auth_service,
        uow=uow,
        expenseitem_service=expenseitem_service,
        customentity_service=customentity_service,
        counterparty_service=counterparty_service,
    )


ExpenseSyncHandlerDep = Annotated[
    ExpenseSyncHandler, Depends(get_expense_sync_handler)
]
