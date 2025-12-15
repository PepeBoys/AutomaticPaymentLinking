"""Клиент для работы с API расходных ордеров."""

from ...payment_base.services.base_client import BasePaymentClient


class CashOutClient(BasePaymentClient):
    """Клиент для работы с API расходных ордеров."""

    @property
    def entity_type(self) -> str:
        return "cashout"
