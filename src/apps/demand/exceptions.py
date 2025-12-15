"""Исключения для работы с отгрузками."""

from ..payable_document_base.exceptions import (
    BaseDocumentException,
    DocumentAPIError,
    DocumentNotFoundError,
)

DemandBaseException = BaseDocumentException
DemandAPIError = DocumentAPIError
DemandNotFoundError = DocumentNotFoundError
