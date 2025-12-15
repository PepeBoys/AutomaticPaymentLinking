"""Pydantic схемы для работы с расходными ордерами."""

from ..payment_base.schemas import (
    Agent,
    BasePaymentResponse,
    LinkedOperation,
    MetaRef,
    Organization,
)


class CashOutResponse(BasePaymentResponse):
    """Ответ API с информацией о расходном ордере."""

    pass
