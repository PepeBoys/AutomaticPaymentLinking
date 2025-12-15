"""Базовые схемы для оплачиваемых документов."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ..payment_base.schemas import MetaRef, Agent, Organization  # type: ignore


class BaseDocumentResponse(BaseModel):
    """Базовый ответ API для документов."""

    id: str
    accountId: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    payedSum: float
    agent: Agent
    organization: Organization
    meta: MetaRef
    project: dict | None = None
    shippedSum: Optional[float] = None
    invoicedSum: Optional[float] = None

    class Config:
        extra = "allow"
