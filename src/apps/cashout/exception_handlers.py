"""Обработчики исключений для cashout."""

from ..payment_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payment_base.exception_handlers import (
    base_payment_exception_handler as cashout_base_exception_handler,
    payment_api_error_handler as cashout_api_error_handler,
    payment_not_found_handler as cashout_not_found_handler,
)
from .exceptions import CashOutAPIError, CashOutBaseException, CashOutNotFoundError

EXCEPTION_HANDLERS = {
    CashOutNotFoundError: cashout_not_found_handler,
    CashOutAPIError: cashout_api_error_handler,
    CashOutBaseException: cashout_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
