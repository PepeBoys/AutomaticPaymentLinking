"""Обработчики исключений для invoiceout."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as invoiceout_base_exception_handler,
    document_api_error_handler as invoiceout_api_error_handler,
    document_not_found_handler as invoiceout_not_found_handler,
)
from .exceptions import InvoiceOutAPIError, InvoiceOutBaseException, InvoiceOutNotFoundError

EXCEPTION_HANDLERS = {
    InvoiceOutNotFoundError: invoiceout_not_found_handler,
    InvoiceOutAPIError: invoiceout_api_error_handler,
    InvoiceOutBaseException: invoiceout_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
