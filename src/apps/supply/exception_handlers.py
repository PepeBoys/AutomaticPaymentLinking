"""Обработчики исключений для supply."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as supply_base_exception_handler,
    document_api_error_handler as supply_api_error_handler,
    document_not_found_handler as supply_not_found_handler,
)
from .exceptions import SupplyAPIError, SupplyBaseException, SupplyNotFoundError

EXCEPTION_HANDLERS = {
    SupplyNotFoundError: supply_not_found_handler,
    SupplyAPIError: supply_api_error_handler,
    SupplyBaseException: supply_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
