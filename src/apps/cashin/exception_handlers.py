"""Обработчики исключений для cashin."""

from ..payment_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payment_base.exception_handlers import (
    base_payment_exception_handler as cashin_base_exception_handler,
    payment_api_error_handler as cashin_api_error_handler,
    payment_not_found_handler as cashin_not_found_handler,
)
from .exceptions import CashInAPIError, CashInBaseException, CashInNotFoundError

EXCEPTION_HANDLERS = {
    CashInNotFoundError: cashin_not_found_handler,
    CashInAPIError: cashin_api_error_handler,
    CashInBaseException: cashin_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
