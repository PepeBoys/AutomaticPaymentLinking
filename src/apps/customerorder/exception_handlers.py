"""Обработчики исключений для customerorder."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as customerorder_base_exception_handler,
    document_api_error_handler as customerorder_api_error_handler,
    document_not_found_handler as customerorder_not_found_handler,
)
from .exceptions import (
    CustomerOrderAPIError,
    CustomerOrderBaseException,
    CustomerOrderNotFoundError,
)

EXCEPTION_HANDLERS = {
    CustomerOrderNotFoundError: customerorder_not_found_handler,
    CustomerOrderAPIError: customerorder_api_error_handler,
    CustomerOrderBaseException: customerorder_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
