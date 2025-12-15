"""Value objects для оплачиваемых документов."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BaseDocumentFilter:
    """Базовый фильтр документов."""

    agent_id: Optional[str] = None
    organization_id: Optional[str] = None
    date_from: Optional[datetime] = None
    prioritize_oldest: bool = True
