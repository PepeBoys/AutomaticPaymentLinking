"""Базовые доменные сущности для платежных документов."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BasePaymentEntity:
    """Базовая сущность платежа."""

    id: str
    account_id: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    agent_id: str
    organization_id: str
    payment_purpose: Optional[str]
    linked_operations: list[dict]
    meta_href: str
    project_meta_href: Optional[str] = None
    sales_channel_meta_href: Optional[str] = None
    expense_item_meta_href: Optional[str] = None
