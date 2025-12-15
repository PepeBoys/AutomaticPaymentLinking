"""Обработчики исключений для purchaseorder."""

from ..payable_document_base.exception_handlers import BASE_EXCEPTION_HANDLERS
from ..payable_document_base.exception_handlers import (
    base_document_exception_handler as purchaseorder_base_exception_handler,
    document_api_error_handler as purchaseorder_api_error_handler,
    document_not_found_handler as purchaseorder_not_found_handler,
)
from .exceptions import (
    PurchaseOrderAPIError,
    PurchaseOrderBaseException,
    PurchaseOrderNotFoundError,
)

EXCEPTION_HANDLERS = {
    PurchaseOrderNotFoundError: purchaseorder_not_found_handler,
    PurchaseOrderAPIError: purchaseorder_api_error_handler,
    PurchaseOrderBaseException: purchaseorder_base_exception_handler,
}

BASE_EXCEPTION_HANDLERS_ALIAS = BASE_EXCEPTION_HANDLERS
