"""Клиент для работы с API исходящих платежей МойСклад."""

from ...payment_base.services.base_client import BasePaymentClient


class PaymentOutClient(BasePaymentClient):
    """Клиент для работы с API исходящих платежей МойСклад."""

    @property
    def entity_type(self) -> str:
        return "paymentout"
