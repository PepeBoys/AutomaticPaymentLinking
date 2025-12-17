from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_session
from src.apps.vendor_api.repository import VendorAccountRepository

from .services.auth_service import MySkladAuthService, build_ms_auth_service


async def get_ms_auth_service(
    account_id: str | None = Header(default=None, alias="X-Account-Id"),
    session: AsyncSession = Depends(get_session),
) -> MySkladAuthService:
    """Загрузить auth-контекст для конкретного аккаунта.

    - Создаёт новый экземпляр `MySkladAuthService` на каждый запрос.
    - Если передан `X-Account-Id`, подтягивает access_token из базы и
      проставляет его в сервис, чтобы downstream-логика работала в рамках
      нужного аккаунта.
    - Если аккаунт не найден или не активен, возвращает 401, чтобы клиент
      повторно активировал приложение.
    """

    auth_service = build_ms_auth_service()

    if not account_id:
        return auth_service

    repo = VendorAccountRepository(session)
    account = await repo.get_by_account_id(account_id)

    if not account or not account.is_active or not account.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is not activated. Please re-run app activation.",
        )

    auth_service.set_access_token(
        account.access_token,
        base_url=settings.ms_base_url,
        account_id=account.account_id,
    )

    return auth_service


AuthSvcDep = Annotated[MySkladAuthService, Depends(get_ms_auth_service)]
