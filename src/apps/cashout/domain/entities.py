"""Доменные сущности расходных ордеров."""

from dataclasses import dataclass

from ...payment_base.domain.entities import BasePaymentEntity


@dataclass
class CashOutEntity(BasePaymentEntity):
    """Доменная сущность расходного ордера."""

    pass
