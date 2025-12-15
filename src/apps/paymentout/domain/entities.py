"""Доменные сущности исходящих платежей."""

from dataclasses import dataclass

from ...payment_base.domain.entities import BasePaymentEntity


@dataclass
class PaymentOutEntity(BasePaymentEntity):
    """Доменная сущность исходящего платежа."""

    pass
