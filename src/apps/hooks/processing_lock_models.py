from sqlalchemy import CheckConstraint, Column, DateTime, String

from src.core.models import Base


class WebhookProcessingLock(Base):
    account_id = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "account_id IS NOT NULL AND account_id != ''",
            name="ck_webhook_processing_account_id_not_empty",
        ),
    )
