"""REST API модуля синхронизации статей расходов."""

import logging

from fastapi import APIRouter

from .dependencies import ExpenseSetupSvcDep, ExpenseSyncSvcDep
from .schemas import (
    ExpenseSyncDiffResponse,
    ExpenseSyncInitResponse,
    ExpenseSyncStatusResponse,
    ExpenseSyncTogglePayload,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=ExpenseSyncStatusResponse)
async def get_status(service: ExpenseSyncSvcDep):
    status = await service.get_status()
    return ExpenseSyncStatusResponse(**status)


@router.get("/diff", response_model=ExpenseSyncDiffResponse)
async def get_diff(service: ExpenseSyncSvcDep):
    """Рассинхронизация зеркала со справочником «Статьи расходов»."""
    diff = await service.compute_diff()
    return ExpenseSyncDiffResponse(**diff)


@router.post("/init", response_model=ExpenseSyncInitResponse)
async def initialize(service: ExpenseSetupSvcDep):
    """Создать/доинициализировать инфраструктуру синхронизации статей расходов."""
    result = await service.initialize()
    return ExpenseSyncInitResponse(
        status="ok" if result.success else "warning",
        account_id=result.account_id,
        mirror_customentity_id=result.mirror_customentity_id,
        counterparty_attribute_id=result.counterparty_attribute_id,
        elements_created=result.elements_created,
        elements_skipped=result.elements_skipped,
        webhooks_created=result.webhooks_created,
        webhooks_existing=result.webhooks_existing,
        errors=result.errors,
    )


@router.post("/toggle")
async def toggle(payload: ExpenseSyncTogglePayload, service: ExpenseSyncSvcDep):
    return await service.set_enabled(payload.enabled)
