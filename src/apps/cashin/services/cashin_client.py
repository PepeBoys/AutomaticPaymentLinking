"""Клиент для работы с API приходных ордеров."""

from ...payment_base.services.base_client import BasePaymentClient


class CashInClient(BasePaymentClient):
    """Клиент для работы с API приходных ордеров."""

    @property
    def entity_type(self) -> str:
        return "cashin"
