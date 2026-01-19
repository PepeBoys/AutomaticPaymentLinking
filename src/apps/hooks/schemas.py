from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PaymentType(str, Enum):
    incoming_payment = "incoming_payment"   # Входящий платеж
    incoming_order = "incoming_order"       # Приходный ордер
    outgoing_payment = "outgoing_payment"   # Исходящий платеж
    outgoing_order = "outgoing_order"       # Расходный ордер


class DocumentType(str, Enum):
    customerorder = "customerorder"  # Заказ покупателя
    invoiceout = "invoiceout"        # Счет покупателя
    demand = "demand"                # Отгрузка
    purchaseorder = "purchaseorder"  # Заказ поставщика
    invoicein = "invoicein"          # Счет поставщика
    supply = "supply"                # Приемка


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
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False


class UpdateLinkSettingsPayload(BaseModel):
    payment_type: PaymentType
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False


class WebhookStatusItem(BaseModel):
    enabled: bool
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False


class StateItem(BaseModel):
    id: str
    name: str
    color: Optional[int] = None


class StatesResponse(BaseModel):
    payment_states: List[StateItem]
    document_states: List[StateItem]
    has_payment_states: bool
    has_document_states: bool


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
    meta: Optional[MetaRef] = None
    moment: Optional[datetime] = None
    uid: Optional[str] = None


class WebhookEvent(BaseModel):
    meta: Optional[MetaRef] = None
    action: Optional[str] = None  # CREATE / UPDATE / DELETE / PROCESSED
    accountId: Optional[str] = None
    updatedFields: Optional[List[str]] = None


class MySkladWebhookPayload(BaseModel):
    """
    Общая структура вебхука:
    {
      "auditContext": {...},
      "events": [ {...}, {...} ]
    }
    """
    auditContext: Optional[AuditContext] = None
    events: List[WebhookEvent] = Field(default_factory=list)
