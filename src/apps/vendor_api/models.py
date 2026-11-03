from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
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
    base_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    app_uid: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )

    # Подписка на решение (из активации МС или GET .../status Vendor API).
    tariff_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tariff_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tariff_trial: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tariff_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Когда подписку последний раз получали от МС (в т.ч. неудачно).
    subscription_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
