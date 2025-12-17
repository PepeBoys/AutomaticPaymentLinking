from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.models import Base


class VendorAccount(Base):
    """Информация об установке решения для аккаунта МойСклад."""

    account_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
    )
    access_token: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
    )
    app_uid: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )


class VendorJwtJti(Base):
    """Использованные идентификаторы JWT для защиты от повторов."""

    jti: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
