"""Клиент для работы с API входящих платежей МойСклад."""

from ...payment_base.services.base_client import BasePaymentClient


class PaymentInClient(BasePaymentClient):
    """Клиент для работы с API входящих платежей МойСклад."""

    @property
    def entity_type(self) -> str:
        return "paymentin"
