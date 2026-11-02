"""Доменные сущности модуля автопроставления статьи доходов."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# Поля конфига с id доп. полей в МС, по которым проверяется готовность.
ATTRIBUTE_FIELDS = (
    "counterparty_attribute_id",
    "paymentin_attribute_id",
    "cashin_attribute_id",
)


@dataclass
class IncomeSyncConfig:
    """Настройки фичи для одного аккаунта МС."""

    ms_account_id: str
    dictionary_id: Optional[str] = None
    counterparty_attribute_id: Optional[str] = None
    paymentin_attribute_id: Optional[str] = None
    cashin_attribute_id: Optional[str] = None
    enabled: bool = False
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_initialized(self) -> bool:
        """Справочник и все три доп. поля созданы."""
        return bool(self.dictionary_id) and all(
            getattr(self, name) for name in ATTRIBUTE_FIELDS
        )

    def payment_attribute_id(self, entity_type: str) -> Optional[str]:
        """id доп. поля «Статья доходов» для paymentin/cashin."""
        return getattr(self, f"{entity_type}_attribute_id", None)
