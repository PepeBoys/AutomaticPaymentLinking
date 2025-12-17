from sqlalchemy import Boolean, Column
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
    ms_account_id = Column(String(64), nullable=True)

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
    )