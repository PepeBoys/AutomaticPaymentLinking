"""Исключения для работы с заказами поставщикам."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

PurchaseOrderBaseException = BaseDocumentException
PurchaseOrderAPIError = DocumentAPIError
PurchaseOrderNotFoundError = DocumentNotFoundError
