from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class PaymentType(str, Enum):
    incoming_payment = "incoming_payment"   # Входящий платеж
    incoming_order = "incoming_order"       # Приходный ордер
    outgoing_payment = "outgoing_payment"   # Исходящий платеж
    outgoing_order = "outgoing_order"       # Расходный ордер


class DocumentType(str, Enum):
    customerorder = "customerorder"  # Заказ покупателя
    invoiceout = "invoiceout"        # Счет покупателя
    demand = "demand"                # Отгрузка


class LinkType(str, Enum):
    sum_and_counterparty = "sum_and_counterparty"          # По сумме и контрагенту
    counterparty = "counterparty"                          # По контрагенту
    payment_purpose_mask = "payment_purpose_mask"          # По маске назначения платежа


class DocumentPriority(str, Enum):
    oldest_first = "oldest_first"       # Сначала старые документы
    newest_first = "newest_first"       # Сначала новые документы


class AutoLinkTogglePayload(BaseModel):
    payment_type: PaymentType
    enabled: bool
    document_type: Optional[DocumentType] = DocumentType.customerorder
    link_type: Optional[LinkType] = LinkType.sum_and_counterparty
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None


class UpdateLinkSettingsPayload(BaseModel):
    payment_type: PaymentType
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None


class WebhookStatusItem(BaseModel):
    enabled: bool
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None


class WebhookStatusResponse(BaseModel):
    webhooks: Dict[str, WebhookStatusItem]


# ===== Схемы для входящих вебхуков МойСклад =====


class MetaRef(BaseModel):
    """
    Универсальные meta, которые МС кладёт в auditContext.meta и event.meta.
    Остальные поля (metadataHref и прочие) Pydantic примет, даже если мы их не описали.
    """
    href: str
    type: str

    class Config:
        extra = "allow"  # не падать, если придут лишние поля


class AuditContext(BaseModel):
    meta: MetaRef
    moment: datetime
    uid: str


class WebhookEvent(BaseModel):
    meta: MetaRef
    action: str  # CREATE / UPDATE / DELETE / PROCESSED
    accountId: str
    updatedFields: Optional[List[str]] = None


class MySkladWebhookPayload(BaseModel):
    """
    Общая структура вебхука:
    {
      "auditContext": {...},
      "events": [ {...}, {...} ]
    }
    """
    auditContext: AuditContext
    events: List[WebhookEvent]