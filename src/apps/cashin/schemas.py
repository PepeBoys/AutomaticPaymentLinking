"""Pydantic схемы для работы с приходными ордерами."""

from ..payment_base.schemas import (
    Agent,
    BasePaymentResponse,
    LinkedOperation,
    MetaRef,
    Organization,
)


class CashInResponse(BasePaymentResponse):
    """Ответ API с информацией о приходном ордере."""

    pass
