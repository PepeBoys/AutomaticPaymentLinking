"""Pydantic-схемы модуля синхронизации статей расходов."""

from typing import List, Optional

from pydantic import BaseModel


class ExpenseSyncStatusResponse(BaseModel):
    enabled: bool
    initialized: bool
    mirror_customentity_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    mappings_count: int = 0
    diagnostic: str = "ok"
    message: Optional[str] = None


class ExpenseSyncDiffEntry(BaseModel):
    expenseitem_id: Optional[str] = None
    element_id: Optional[str] = None
    source_name: Optional[str] = None
    mirror_name: Optional[str] = None
    changed_fields: List[str] = []


class ExpenseSyncDiffResponse(BaseModel):
    status: str
    in_sync: bool
    source_count: int = 0
    mirror_count: int = 0
    missing_in_mirror: List[ExpenseSyncDiffEntry] = []
    orphan_in_mirror: List[ExpenseSyncDiffEntry] = []
    changed: List[ExpenseSyncDiffEntry] = []
    extra_in_mirror: List[ExpenseSyncDiffEntry] = []
    duplicate_in_mirror: List[ExpenseSyncDiffEntry] = []


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
