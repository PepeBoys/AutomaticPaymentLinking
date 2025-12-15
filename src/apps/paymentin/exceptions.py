"""Исключения для работы с входящими платежами."""

from ..payment_base.exceptions import (
    BasePaymentException,
    PaymentAPIError,
    PaymentNotFoundError,
)

PaymentInBaseException = BasePaymentException
PaymentInAPIError = PaymentAPIError
PaymentInNotFoundError = PaymentNotFoundError
