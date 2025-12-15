"""Обработчики исключений для paymentin."""

from ..payment_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payment_base.exception_handlers import (
    base_payment_exception_handler as paymentin_base_exception_handler,
    payment_api_error_handler as paymentin_api_error_handler,
    payment_not_found_handler as paymentin_not_found_handler,
)
from .exceptions import (
    PaymentInAPIError,
    PaymentInBaseException,
    PaymentInNotFoundError,
)

EXCEPTION_HANDLERS = {
    PaymentInNotFoundError: paymentin_not_found_handler,
    PaymentInAPIError: paymentin_api_error_handler,
    PaymentInBaseException: paymentin_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
