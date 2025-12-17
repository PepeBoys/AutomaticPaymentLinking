"""Доменные сущности."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..schemas import DocumentPriority, DocumentType, LinkType, PaymentType


@dataclass
class WebhookEntity:
    """Доменная сущность вебхука."""
    
    payment_type: PaymentType
    entity_type: str
    action: str
    url: str
    ms_webhook_id: str
    enabled: bool
    document_type: DocumentType = DocumentType.customerorder
    link_type: LinkType = LinkType.sum_and_counterparty
    document_priority: DocumentPriority = DocumentPriority.oldest_first
    payment_purpose_mask: Optional[str] = None
    payment_status_on_success: Optional[str] = None
    payment_status_on_failure: Optional[str] = None
    document_status_on_success: Optional[str] = None
    transfer_project_to_payment: bool = False
    check_document_organization: bool = False
    id: Optional[int] = None
    ms_href: Optional[str] = None
    ms_account_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def activate(self) -> None:
        """Активировать вебхук."""
        self.enabled = True
    
    def deactivate(self) -> None:
        """Деактивировать вебхук."""
        self.enabled = False
    
    def is_active(self) -> bool:
        """Проверить, активен ли вебхук."""
        return self.enabled


@dataclass
class WebhookOperationResult:
    """Результат операции с вебхуком."""
    
    operation: str
    success: bool
    webhook_entity: Optional[WebhookEntity] = None
    message: Optional[str] = None
    error: Optional[str] = None
    details: dict = field(default_factory=dict)
    
    def is_skipped(self) -> bool:
        """Проверить, была ли операция пропущена."""
        return self.operation.startswith("skipped_")
    
    def is_error(self) -> bool:
        """Проверить, произошла ли ошибка."""
        return self.operation.startswith("error_") or not self.success