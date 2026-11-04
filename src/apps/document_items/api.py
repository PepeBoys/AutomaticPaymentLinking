"""REST API статей доходов/расходов в первичных документах."""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .exceptions import DocumentItemsBaseException
from .services.settings_service import DocumentItemsSettingsService

router = APIRouter()


async def get_document_items_settings_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    session: AsyncSession = Depends(get_session),
) -> DocumentItemsSettingsService:
    return DocumentItemsSettingsService(auth_service, session)


SettingsSvcDep = Annotated[
    DocumentItemsSettingsService, Depends(get_document_items_settings_service)
]


class DocumentItemsModesPayload(BaseModel):
    income_mode: Optional[str] = None
    expense_mode: Optional[str] = None


class DocumentItemsInitResponse(BaseModel):
    status: str
    created: List[str] = []
    errors: List[str] = []


@router.get("/status")
async def get_status(service: SettingsSvcDep):
    return await service.get_status()


@router.post("/init", response_model=DocumentItemsInitResponse)
async def initialize(service: SettingsSvcDep):
    """Создать доп. поля «Статья доходов/расходов» в документах."""
    result = await service.initialize()
    return DocumentItemsInitResponse(
        status="ok" if not result.errors else "warning",
        created=result.created,
        errors=result.errors,
    )


@router.post("/settings")
async def set_modes(payload: DocumentItemsModesPayload, service: SettingsSvcDep):
    try:
        return await service.set_modes(payload.income_mode, payload.expense_mode)
    except DocumentItemsBaseException as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
