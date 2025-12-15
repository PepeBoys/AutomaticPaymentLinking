"""Исключения для работы с поступлениями."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

SupplyBaseException = BaseDocumentException
SupplyAPIError = DocumentAPIError
SupplyNotFoundError = DocumentNotFoundError
