"""Доменные сущности входящих платежей."""

from dataclasses import dataclass

from ...payment_base.domain.entities import BasePaymentEntity


@dataclass
class PaymentInEntity(BasePaymentEntity):
    """Доменная сущность входящего платежа."""

    pass
