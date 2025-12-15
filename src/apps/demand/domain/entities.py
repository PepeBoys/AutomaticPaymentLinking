"""Доменные сущности отгрузок."""

from dataclasses import dataclass

from ...payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class DemandEntity(BasePayableDocumentEntity):
    """Доменная сущность отгрузки."""

    pass
