"""Dependency Injection для модуля автопроставления статьи доходов."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

from ..cashin.dependencies import get_cashin_service
from ..cashin.services.cashin_service import CashInService
from ..counterparty.dependencies import get_counterparty_service
from ..counterparty.services.counterparty_service import CounterpartyService
from ..customentity.dependencies import get_customentity_service
from ..customentity.services.customentity_service import CustomEntityService
from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from ..paymentin.dependencies import get_paymentin_service
from ..paymentin.services.paymentin_service import PaymentInService
from .services.income_sync_service import IncomeSyncService
from .services.setup_service import IncomeItemSetupService
from .services.sync_service import IncomeSyncHandler
from .uow.unit_of_work import IncomeSyncUnitOfWork


async def get_income_sync_uow(
    session: AsyncSession = Depends(get_session),
) -> IncomeSyncUnitOfWork:
    return IncomeSyncUnitOfWork(session)


async def get_income_setup_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: IncomeSyncUnitOfWork = Depends(get_income_sync_uow),
    customentity_service: CustomEntityService = Depends(get_customentity_service),
    counterparty_service: CounterpartyService = Depends(get_counterparty_service),
    paymentin_service: PaymentInService = Depends(get_paymentin_service),
    cashin_service: CashInService = Depends(get_cashin_service),
) -> IncomeItemSetupService:
    return IncomeItemSetupService(
        auth_service=auth_service,
        uow=uow,
        customentity_service=customentity_service,
        counterparty_service=counterparty_service,
        paymentin_service=paymentin_service,
        cashin_service=cashin_service,
    )


IncomeSetupSvcDep = Annotated[IncomeItemSetupService, Depends(get_income_setup_service)]


async def get_income_sync_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: IncomeSyncUnitOfWork = Depends(get_income_sync_uow),
    customentity_service: CustomEntityService = Depends(get_customentity_service),
    counterparty_service: CounterpartyService = Depends(get_counterparty_service),
    paymentin_service: PaymentInService = Depends(get_paymentin_service),
    cashin_service: CashInService = Depends(get_cashin_service),
) -> IncomeSyncService:
    return IncomeSyncService(
        auth_service=auth_service,
        uow=uow,
        customentity_service=customentity_service,
        counterparty_service=counterparty_service,
        paymentin_service=paymentin_service,
        cashin_service=cashin_service,
    )


IncomeSyncSvcDep = Annotated[IncomeSyncService, Depends(get_income_sync_service)]


async def get_income_sync_handler(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    uow: IncomeSyncUnitOfWork = Depends(get_income_sync_uow),
    counterparty_service: CounterpartyService = Depends(get_counterparty_service),
) -> IncomeSyncHandler:
    return IncomeSyncHandler(
        auth_service=auth_service,
        uow=uow,
        counterparty_service=counterparty_service,
    )


IncomeSyncHandlerDep = Annotated[IncomeSyncHandler, Depends(get_income_sync_handler)]
