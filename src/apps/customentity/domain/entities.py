"""Доменные сущности пользовательских справочников (customentity)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CustomEntityDictionary:
    """Пользовательский справочник (метаданные)."""

    id: str
    name: str
    meta_href: str


@dataclass
class CustomEntityElementEntity:
    """Элемент пользовательского справочника."""

    id: str
    name: str
    meta_href: str
    code: Optional[str] = None
    description: Optional[str] = None
    external_code: Optional[str] = None
    account_id: Optional[str] = None
    updated: Optional[str] = None
