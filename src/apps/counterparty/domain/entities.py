"""Доменные сущности контрагентов (counterparty)."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CounterpartyEntity:
    """Контрагент МойСклад.

    Доп. поля (attributes) хранятся в сыром виде — это список объектов доп.
    полей со значениями (см. «Работа с дополнительными полями» МС). Для доп.
    поля типа «справочник» value — это объект {meta, name}.
    """

    id: str
    name: str
    meta_href: str
    attributes: list[dict] = field(default_factory=list)
    account_id: Optional[str] = None

    def get_attribute(self, attribute_id: str) -> Optional[dict]:
        """Найти доп. поле по его id (id метаданных доп. поля)."""
        for attr in self.attributes:
            if attr.get("id") == attribute_id:
                return attr
        return None

    def get_attribute_value(self, attribute_id: str) -> Optional[Any]:
        """Получить значение доп. поля по его id."""
        attr = self.get_attribute(attribute_id)
        return attr.get("value") if attr else None
