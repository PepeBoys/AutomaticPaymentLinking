from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, String

from src.core.models import Base

from .schemas import DocumentPriority, DocumentType, LinkType, PaymentType


class WebhookSubscription(Base):

    payment_type = Column(
        SAEnum(PaymentType, name="payment_type_enum"),
        nullable=False,
        index=True,
    )

    entity_type = Column(String(255), nullable=False)
    action = Column(String(32), nullable=False)
    url = Column(String(255), nullable=False)

    ms_webhook_id = Column(String(64), unique=True, nullable=False, index=True)
    ms_href = Column(String(512), nullable=True)
    ms_account_id = Column(String(64), nullable=False, index=True)

    enabled = Column(Boolean, nullable=False, default=True, index=True)

    document_type = Column(
        SAEnum(DocumentType, name="document_type_enum"),
        nullable=False,
        default=DocumentType.customerorder,
        server_default="customerorder",
    )

    link_type = Column(
        SAEnum(LinkType, name="link_type_enum"),
        nullable=False,
        default=LinkType.sum_and_counterparty,
        server_default="sum_and_counterparty",
    )

    document_priority = Column(
        SAEnum(DocumentPriority, name="document_priority_enum"),
        nullable=False,
        default=DocumentPriority.oldest_first,
        server_default="oldest_first",
    )

    payment_purpose_mask = Column(
        String(512),
        nullable=True,
    )

    payment_status_on_success = Column(
        String(64),
        nullable=True,
    )
    payment_status_on_failure = Column(
        String(64),
        nullable=True,
    )

    document_status_on_success = Column(
        String(64),
        nullable=True,
    )
    document_status_on_failure = Column(
        String(64),
        nullable=True,
    )

    transfer_project_to_payment = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    transfer_sales_channel_to_payment = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    check_document_organization = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    __table_args__ = (
        Index(
            "ix_webhook_payment_enabled",
            "payment_type",
            "enabled",
        ),
        Index(
            "ix_webhook_entity_action_url",
            "entity_type",
            "action",
            "url",
        ),
        Index(
            "ix_webhook_account_payment",
            "ms_account_id",
            "payment_type",
            unique=True,
        ),
        CheckConstraint(
            "ms_account_id IS NOT NULL AND ms_account_id != ''",
            name="ck_webhook_account_id_not_empty",
        ),
    )


class WebhookRequest(Base):
    request_id = Column(String(64), nullable=False, unique=True, index=True)
    ms_account_id = Column(String(64), nullable=True, index=True)
    events_count = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="accepted")
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "request_id IS NOT NULL AND request_id != ''",
            name="ck_webhook_request_id_not_empty",
        ),
    )


class PendingPaymentLink(Base):
    """Временная таблица для отслеживания запланированных привязок платежей к документам."""

    account_id = Column(String(64), nullable=False, index=True)
    document_id = Column(String(64), nullable=False, index=True)
    payment_id = Column(String(64), nullable=False, index=True)
    linked_sum = Column(Float, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_pending_link_account_document",
            "account_id",
            "document_id",
        ),
        CheckConstraint(
            "account_id IS NOT NULL AND account_id != ''",
            name="ck_pending_link_account_id_not_empty",
        ),
        CheckConstraint(
            "document_id IS NOT NULL AND document_id != ''",
            name="ck_pending_link_document_id_not_empty",
        ),
        CheckConstraint(
            "linked_sum > 0",
            name="ck_pending_link_positive_sum",
        ),
    )
