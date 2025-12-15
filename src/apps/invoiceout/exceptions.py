"""Исключения для работы со счетами покупателю."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

InvoiceOutBaseException = BaseDocumentException
InvoiceOutAPIError = DocumentAPIError
InvoiceOutNotFoundError = DocumentNotFoundError
