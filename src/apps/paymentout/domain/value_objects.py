"""Value Objects для входящих платежей."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PaymentOutFilter:
    """Фильтр для поиска входящих платежей (Value Object)."""
    
    agent_id: Optional[str] = None
    sum_value: Optional[float] = None
    sum_tolerance: float = 0.01
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    def to_moysklad_filter(self) -> str:
        """
        Преобразовать в строку фильтра для API МойСклад.
        
        Returns:
            Строка фильтра для параметра filter
        """
        filters = []
        
        if self.agent_id:
            filters.append(f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{self.agent_id}")
        
        if self.sum_value is not None:
            sum_min = self.sum_value - self.sum_tolerance
            sum_max = self.sum_value + self.sum_tolerance
            filters.append(f"sum>={sum_min}")
            filters.append(f"sum<={sum_max}")
        
        if self.date_from:
            filters.append(f"moment>={self.date_from.isoformat()}")
        
        if self.date_to:
            filters.append(f"moment<={self.date_to.isoformat()}")
        
        return ";".join(filters) if filters else ""