"""Доменные сущности поступлений."""

from dataclasses import dataclass

from ...payable_document_base.domain.entities import BasePayableDocumentEntity


@dataclass
class SupplyEntity(BasePayableDocumentEntity):
    """Доменная сущность поступления."""

    pass
