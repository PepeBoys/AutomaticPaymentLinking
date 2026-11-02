"""REST API модуля автопроставления статьи доходов."""

import logging

from fastapi import APIRouter

from .dependencies import IncomeSetupSvcDep, IncomeSyncSvcDep
from .schemas import (
    IncomeSyncInitResponse,
    IncomeSyncStatusResponse,
    IncomeSyncTogglePayload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=IncomeSyncStatusResponse)
async def get_status(service: IncomeSyncSvcDep):
    status = await service.get_status()
    return IncomeSyncStatusResponse(**status)


@router.post("/init", response_model=IncomeSyncInitResponse)
async def initialize(service: IncomeSetupSvcDep):
    """Создать/доинициализировать справочник, доп. поля и вебхуки статьи доходов."""
    result = await service.initialize()
    return IncomeSyncInitResponse(
        status="ok" if result.success else "warning",
        account_id=result.account_id,
        dictionary_id=result.dictionary_id,
        counterparty_attribute_id=result.counterparty_attribute_id,
        paymentin_attribute_id=result.paymentin_attribute_id,
        cashin_attribute_id=result.cashin_attribute_id,
        webhooks_created=result.webhooks_created,
        webhooks_existing=result.webhooks_existing,
        errors=result.errors,
    )


@router.post("/toggle")
async def toggle(payload: IncomeSyncTogglePayload, service: IncomeSyncSvcDep):
    return await service.set_enabled(payload.enabled)
