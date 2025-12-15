"""Доменные сущности заказов покупателей."""

from dataclasses import dataclass

from ..payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class CustomerOrderEntity(BasePayableDocumentEntity):
    """Доменная сущность заказа покупателя."""

    pass
