"""Pydantic-схемы модуля синхронизации статей расходов."""

from typing import List, Optional

from pydantic import BaseModel


class ExpenseSyncStatusResponse(BaseModel):
    enabled: bool
    initialized: bool
    mirror_customentity_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    mappings_count: int = 0


class ExpenseSyncTogglePayload(BaseModel):
    enabled: bool


class ExpenseSyncInitResponse(BaseModel):
    status: str
    account_id: str
    mirror_customentity_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    elements_created: int = 0
    elements_skipped: int = 0
    webhooks_created: int = 0
    webhooks_existing: int = 0
    errors: List[str] = []
