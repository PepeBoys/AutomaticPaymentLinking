"""Dependency Injection для пользовательских справочников."""

from typing import Annotated

from fastapi import Depends

from ..ms_auth.dependencies import get_ms_auth_service
from ..ms_auth.services.auth_service import MySkladAuthService
from .services.customentity_service import CustomEntityService


async def get_customentity_service(
    auth_service: MySkladAuthService = Depends(get_ms_auth_service),
) -> CustomEntityService:
    """Получить сервис пользовательских справочников."""
    return CustomEntityService(auth_service=auth_service)


CustomEntitySvcDep = Annotated[CustomEntityService, Depends(get_customentity_service)]
