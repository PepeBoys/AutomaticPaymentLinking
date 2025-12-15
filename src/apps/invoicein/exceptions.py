"""Исключения для работы со счетами поставщиков."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

InvoiceInBaseException = BaseDocumentException
InvoiceInAPIError = DocumentAPIError
InvoiceInNotFoundError = DocumentNotFoundError
