"""Базовые доменные сущности для платежных документов."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


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
    # Доп. поля в сыром виде МС: [{id, name, type, value}, ...]
    attributes: list[dict] = field(default_factory=list)

    def get_attribute_value(self, attribute_id: str) -> Optional[Any]:
        """Значение доп. поля по id его метаданных (None, если не заполнено)."""
        for attr in self.attributes:
            if attr.get("id") == attribute_id:
                return attr.get("value")
        return None
