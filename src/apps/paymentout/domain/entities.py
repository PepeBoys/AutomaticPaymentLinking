"""Доменные сущности входящих платежей."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PaymentOutEntity:
    """Доменная сущность входящего платежа."""

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
