"""Pydantic схемы для работы с исходящими платежами."""

from ..payment_base.schemas import (
    Agent,
    BasePaymentResponse,
    LinkedOperation,
    MetaRef,
    Organization,
)


class PaymentOutResponse(BasePaymentResponse):
    """Ответ API с информацией об исходящем платеже."""

    pass
