"""Доменные сущности модуля синхронизации статей расходов."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExpenseSyncConfig:
    """Настройки фичи для одного аккаунта МС."""

    ms_account_id: str
    mirror_customentity_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    enabled: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_initialized(self) -> bool:
        """Инфраструктура (справочник + доп. поле) создана."""
        return bool(self.mirror_customentity_id and self.counterparty_attribute_id)


@dataclass
class ExpenseItemMappingEntity:
    """Соответствие статьи расходов и элемента справочника-зеркала."""

    ms_account_id: str
    expenseitem_id: str
    customentity_element_id: str
    id: Optional[int] = None
