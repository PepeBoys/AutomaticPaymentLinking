"""Исключения для работы с заказами покупателей."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

CustomerOrderBaseException = BaseDocumentException
CustomerOrderAPIError = DocumentAPIError
CustomerOrderNotFoundError = DocumentNotFoundError
