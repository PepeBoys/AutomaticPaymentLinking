"""Обработчики исключений для demand."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as demand_base_exception_handler,
    document_api_error_handler as demand_api_error_handler,
    document_not_found_handler as demand_not_found_handler,
)
from .exceptions import DemandAPIError, DemandBaseException, DemandNotFoundError

EXCEPTION_HANDLERS = {
    DemandNotFoundError: demand_not_found_handler,
    DemandAPIError: demand_api_error_handler,
    DemandBaseException: demand_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
