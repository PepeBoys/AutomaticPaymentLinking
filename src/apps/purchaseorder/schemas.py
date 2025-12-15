"""Pydantic схемы для работы с заказами покупателя."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MetaRef(BaseModel):
    """Метаданные ссылки на сущность."""
    href: str
    type: str
    mediaType: str = "application/json"


class Agent(BaseModel):
    """Контрагент."""
    meta: MetaRef


class Organization(BaseModel):
    """Организация."""
    meta: MetaRef


class PurchaseOrderResponse(BaseModel):
    """Ответ API с информацией о заказе покупателя."""
    id: str
    accountId: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    payedSum: float
    shippedSum: float
    invoicedSum: float
    agent: Agent
    organization: Organization
    meta: MetaRef
    
    class Config:
        extra = "allow"


class PurchaseOrderListResponse(BaseModel):
    """Ответ API со списком заказов."""
    context: dict
    meta: dict
    rows: list[PurchaseOrderResponse]


class PurchaseOrderSearchParams(BaseModel):
    """Параметры поиска заказов покупателя."""
    agent_id: Optional[str] = None
    sum_from: Optional[float] = None
    sum_to: Optional[float] = None
    moment_from: Optional[datetime] = None
    moment_to: Optional[datetime] = None
    limit: int = 100
    offset: int = 0