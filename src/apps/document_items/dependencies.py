"""Dependency Injection для статей в первичных документах."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.sync_service import DocumentItemsHandler


async def get_document_items_handler(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
    session: AsyncSession = Depends(get_session),
) -> DocumentItemsHandler:
    return DocumentItemsHandler(auth_service, session)


DocumentItemsHandlerDep = Annotated[
    DocumentItemsHandler, Depends(get_document_items_handler)
]
