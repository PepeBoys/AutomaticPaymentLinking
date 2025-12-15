"""Доменные сущности заказов покупателя."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CustomerOrderEntity:
    """Доменная сущность заказа покупателя."""
    
    id: str
    account_id: str
    name: str
    moment: datetime
    applicable: bool
    sum: float
    payed_sum: float
    shipped_sum: float
    invoiced_sum: float
    agent_id: str
    organization_id: str
    meta_href: str
    project_meta_href: Optional[str] = None
    
    def is_fully_paid(self) -> bool:
        """Проверить, полностью ли оплачен заказ."""
        return self.payed_sum >= self.sum
    
    def is_partially_paid(self) -> bool:
        """Проверить, частично ли оплачен заказ."""
        return 0 < self.payed_sum < self.sum
    
    def get_unpaid_amount(self) -> float:
        """Получить неоплаченную сумму."""
        return max(0, self.sum - self.payed_sum)
    
    def matches_sum(self, payment_sum: float, tolerance: float = 0.01) -> bool:
        """
        Проверить, совпадает ли сумма заказа с суммой платежа.
        
        Args:
            payment_sum: Сумма платежа
            tolerance: Допустимая погрешность
            
        Returns:
            True если суммы совпадают с учетом tolerance
        """
        return abs(self.sum - payment_sum) <= tolerance
    
    def matches_unpaid_sum(self, payment_sum: float, tolerance: float = 0.01) -> bool:
        """
        Проверить, совпадает ли неоплаченная сумма с суммой платежа.
        
        Args:
            payment_sum: Сумма платежа
            tolerance: Допустимая погрешность
            
        Returns:
            True если неоплаченная сумма совпадает с платежом
        """
        unpaid = self.get_unpaid_amount()
        return abs(unpaid - payment_sum) <= tolerance