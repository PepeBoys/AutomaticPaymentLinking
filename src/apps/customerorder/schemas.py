"""Pydantic схемы для работы с заказами покупателей."""

from ..payable_document_base.schemas import BaseDocumentResponse

class CustomerOrderResponse(BaseDocumentResponse):
    """Ответ API с информацией о заказе покупателя."""

    pass
