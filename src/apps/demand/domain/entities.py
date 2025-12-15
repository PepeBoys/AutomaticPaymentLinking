"""Доменные сущности отгрузок (demand)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DemandEntity:
    """Доменная сущность отгрузки."""

    id: str
    account_id: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    payed_sum: float
    agent_id: str
    organization_id: str
    meta_href: str
    project_meta_href: str | None = None

    def is_fully_paid(self) -> bool:
        """Проверить, полностью ли оплачена отгрузка."""

        return self.payed_sum >= self.sum

    def get_unpaid_amount(self) -> float:
        """Получить неоплаченную сумму."""

        return max(0, self.sum - self.payed_sum)

    def matches_sum(self, payment_sum: float, tolerance: float = 0.01) -> bool:
        """Проверить, совпадает ли сумма отгрузки с суммой платежа."""

        return abs(self.sum - payment_sum) <= tolerance

    def matches_unpaid_sum(self, payment_sum: float, tolerance: float = 0.01) -> bool:
        """Проверить, совпадает ли неоплаченная сумма с суммой платежа."""

        return abs(self.get_unpaid_amount() - payment_sum) <= tolerance
