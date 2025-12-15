"""Pydantic схемы для работы с заказами поставщикам."""

from ..payable_document_base.schemas import BaseDocumentResponse

class PurchaseOrderResponse(BaseDocumentResponse):
    """Ответ API с информацией о заказе поставщику."""

    pass
