"""Dependency Injection для тарифов."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .service import TariffService


async def get_tariff_service(
    session: AsyncSession = Depends(get_session),
) -> TariffService:
    return TariffService(session)


TariffSvcDep = Annotated[TariffService, Depends(get_tariff_service)]


def require_feature(feature: str):
    """Зависимость эндпоинта: 403, если функция не входит в тариф аккаунта."""

    async def dependency(
        auth_service: MySkladAuthService = Depends(get_ms_auth_service),
        tariffs: TariffService = Depends(get_tariff_service),
    ) -> None:
        account_id = auth_service.get_account_id()
        if not await tariffs.has_feature(account_id, feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=tariffs.locked_message(feature),
            )

    return Depends(dependency)
