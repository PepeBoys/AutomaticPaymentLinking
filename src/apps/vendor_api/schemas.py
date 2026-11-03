from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class AccessItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    resource: str | None = None
    scope: list[str] | None = None
    permissions: dict[str, Any] | None = None
    access_token: str | None = None


class ActivationPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    appUid: str
    accountName: str | None = None
    cause: str | None = None
    access: list[AccessItem] = Field(default_factory=list)
    subscription: dict[str, Any] | None = None
    additional: dict[str, Any] | None = None


class ActivationResponse(BaseModel):
    status: str = "Activated"


class VendorEventPayload(BaseModel):
    eventType: str
    data: Dict[str, Any] | None = None
    moment: datetime | None = None


class DeactivationPayload(BaseModel):
    """Тело DELETE при деактивации: Uninstall или Suspend (приостановка за неоплату)."""

    model_config = ConfigDict(extra="allow")

    cause: str | None = None
