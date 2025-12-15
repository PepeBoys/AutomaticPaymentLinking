"""Pydantic схемы для работы с приходными ордерами."""

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


class LinkedOperation(BaseModel):
    """Связанная операция (документ)."""
    meta: MetaRef
    linkedSum: Optional[float] = None


class CashInResponse(BaseModel):
    """Ответ API с информацией о приходном ордере."""
    id: str
    accountId: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    agent: Agent
    organization: Organization
    paymentPurpose: Optional[str] = None
    operations: list[LinkedOperation] = []
    meta: MetaRef
    
    class Config:
        extra = "allow"