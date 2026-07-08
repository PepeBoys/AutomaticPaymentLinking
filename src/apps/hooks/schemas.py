from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator

from .purpose_templates import (
    MAX_TEMPLATE_LENGTH,
    MAX_TEMPLATES,
    normalize_masks_input,
    validate_templates,
)


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


def _validate_masks_payload(
    link_type: Optional[LinkType], masks: List[str], require_for_mask_mode: bool
) -> None:
    """Общая валидация шаблонов в payload'ах настроек.

    Полные правила применяются только в режиме привязки по шаблону; в остальных
    режимах шаблоны хранятся как есть (round-trip), но с ограничением количества
    и длины, чтобы не раздувать БД.
    """
    if require_for_mask_mode and link_type == LinkType.payment_purpose_mask:
        errors = validate_templates(masks)
        if errors:
            raise ValueError("Шаблоны назначения платежа: " + "; ".join(errors))
        return

    if len(masks) > MAX_TEMPLATES:
        raise ValueError(f"Допускается не более {MAX_TEMPLATES} шаблонов")
    for mask in masks:
        if len(mask) > MAX_TEMPLATE_LENGTH:
            raise ValueError(
                f"Длина шаблона не должна превышать {MAX_TEMPLATE_LENGTH} символов"
            )


class AutoLinkTogglePayload(BaseModel):
    payment_type: PaymentType
    enabled: bool
    document_type: Optional[DocumentType] = DocumentType.customerorder
    link_type: Optional[LinkType] = LinkType.sum_and_counterparty
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    # Принимает и строку (legacy), и список строк; нормализуется к списку.
    payment_purpose_mask: List[str] = []
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False

    @field_validator("payment_purpose_mask", mode="before")
    @classmethod
    def _normalize_masks(cls, value):
        return normalize_masks_input(value)

    @model_validator(mode="after")
    def _check_masks(self):
        # Выключение вебхука не должно блокироваться невалидными шаблонами
        # (например, оставшимися после миграции).
        _validate_masks_payload(
            self.link_type, self.payment_purpose_mask, require_for_mask_mode=self.enabled
        )
        return self


class UpdateLinkSettingsPayload(BaseModel):
    payment_type: PaymentType
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    # Принимает и строку (legacy), и список строк; нормализуется к списку.
    payment_purpose_mask: List[str] = []
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False

    @field_validator("payment_purpose_mask", mode="before")
    @classmethod
    def _normalize_masks(cls, value):
        return normalize_masks_input(value)

    @model_validator(mode="after")
    def _check_masks(self):
        _validate_masks_payload(
            self.link_type, self.payment_purpose_mask, require_for_mask_mode=True
        )
        return self


class WebhookStatusItem(BaseModel):
    enabled: bool
    document_type: DocumentType
    link_type: LinkType
    document_priority: Optional[DocumentPriority] = DocumentPriority.oldest_first
    payment_purpose_mask: List[str] = []
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    transfer_sales_channel_to_payment: bool = False
    check_document_organization: bool = False

    @field_validator("payment_purpose_mask", mode="before")
    @classmethod
    def _normalize_masks(cls, value):
        return normalize_masks_input(value)


class TestPurposeTemplatePayload(BaseModel):
    """Запрос проверки шаблонов на примере назначения платежа."""

    payment_purpose: str = ""
    templates: List[str] = []

    @field_validator("templates", mode="before")
    @classmethod
    def _normalize_templates(cls, value):
        return normalize_masks_input(value)


class PurposeTemplateTestResult(BaseModel):
    template: str
    valid: bool
    errors: List[str] = []
    matched: bool = False
    name: Optional[str] = None
    moment: Optional[str] = None


class TestPurposeTemplateResponse(BaseModel):
    results: List[PurposeTemplateTestResult]
    # Индекс шаблона, который сработал бы при реальной привязке (первый совпавший).
    matched_index: Optional[int] = None


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