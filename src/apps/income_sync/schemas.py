"""Pydantic-схемы модуля автопроставления статьи доходов."""

from typing import List, Optional

from pydantic import BaseModel


class IncomeSyncStatusResponse(BaseModel):
    enabled: bool
    initialized: bool
    dictionary_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    paymentin_attribute_id: Optional[str] = None
    cashin_attribute_id: Optional[str] = None
    diagnostic: str = "ok"
    message: Optional[str] = None


class IncomeSyncTogglePayload(BaseModel):
    enabled: bool


class IncomeSyncInitResponse(BaseModel):
    status: str
    account_id: str
    dictionary_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    paymentin_attribute_id: Optional[str] = None
    cashin_attribute_id: Optional[str] = None
    webhooks_created: int = 0
    webhooks_existing: int = 0
    errors: List[str] = []
