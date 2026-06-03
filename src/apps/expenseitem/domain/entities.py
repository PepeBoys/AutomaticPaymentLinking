"""Доменные сущности статей расходов."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExpenseItemEntity:
    """Статья расходов (expenseitem) МойСклад."""

    id: str
    name: str
    meta_href: str
    description: Optional[str] = None
    code: Optional[str] = None
    external_code: Optional[str] = None
    account_id: Optional[str] = None
    updated: Optional[str] = None
