"""Исключения для работы с исходящими платежами."""

from ..payment_base.exceptions import (
    BasePaymentException,
    PaymentAPIError,
    PaymentNotFoundError,
)

PaymentOutBaseException = BasePaymentException
PaymentOutAPIError = PaymentAPIError
PaymentOutNotFoundError = PaymentNotFoundError
