"""Исключения для работы с приходными ордерами."""

from ..payment_base.exceptions import (
    BasePaymentException,
    PaymentAPIError,
    PaymentNotFoundError,
)

CashInBaseException = BasePaymentException
CashInAPIError = PaymentAPIError
CashInNotFoundError = PaymentNotFoundError
