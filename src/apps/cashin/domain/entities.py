"""Доменные сущности приходных ордеров."""

from dataclasses import dataclass

from ...payment_base.domain.entities import BasePaymentEntity


@dataclass
class CashInEntity(BasePaymentEntity):
    """Доменная сущность приходного ордера."""

    pass
