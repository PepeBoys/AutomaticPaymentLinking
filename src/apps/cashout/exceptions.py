"""Исключения для работы с расходными ордерами."""

from ..payment_base.exceptions import (
    BasePaymentException,
    PaymentAPIError,
    PaymentNotFoundError,
)

CashOutBaseException = BasePaymentException
CashOutAPIError = PaymentAPIError
CashOutNotFoundError = PaymentNotFoundError
