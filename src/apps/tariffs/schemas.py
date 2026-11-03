"""Pydantic-схемы тарифов."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class FeatureStatus(BaseModel):
    label: str
    available: bool
    required_tariffs: List[str] = []
    message: Optional[str] = None


class TariffResponse(BaseModel):
    tariffs_enabled: bool
    known: bool
    tariff_name: Optional[str] = None
    trial: Optional[bool] = None
    expiry: Optional[datetime] = None
    features: Dict[str, FeatureStatus]
