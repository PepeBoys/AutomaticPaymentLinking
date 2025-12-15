"""Value objects для платежей."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BasePaymentFilter:
    """Базовый фильтр платежей."""

    agent_id: Optional[str] = None
    organization_id: Optional[str] = None
    project_href: Optional[str] = None
