"""Обработчики исключений для invoicein."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as invoicein_base_exception_handler,
    document_api_error_handler as invoicein_api_error_handler,
    document_not_found_handler as invoicein_not_found_handler,
)
from .exceptions import InvoiceInAPIError, InvoiceInBaseException, InvoiceInNotFoundError

EXCEPTION_HANDLERS = {
    InvoiceInNotFoundError: invoicein_not_found_handler,
    InvoiceInAPIError: invoicein_api_error_handler,
    InvoiceInBaseException: invoicein_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
