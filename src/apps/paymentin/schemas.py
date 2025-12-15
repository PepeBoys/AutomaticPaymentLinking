"""Pydantic схемы для работы с входящими платежами."""

from ..payment_base.schemas import (
    Agent,
    BasePaymentResponse,
    LinkedOperation,
    MetaRef,
    Organization,
)


class PaymentInResponse(BasePaymentResponse):
    """Ответ API с информацией о входящем платеже."""

    pass
