"""Обработчики исключений для paymentout."""

from ..payment_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payment_base.exception_handlers import (
    base_payment_exception_handler as paymentout_base_exception_handler,
    payment_api_error_handler as paymentout_api_error_handler,
    payment_not_found_handler as paymentout_not_found_handler,
)
from .exceptions import (
    PaymentOutAPIError,
    PaymentOutBaseException,
    PaymentOutNotFoundError,
)

EXCEPTION_HANDLERS = {
    PaymentOutNotFoundError: paymentout_not_found_handler,
    PaymentOutAPIError: paymentout_api_error_handler,
    PaymentOutBaseException: paymentout_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
