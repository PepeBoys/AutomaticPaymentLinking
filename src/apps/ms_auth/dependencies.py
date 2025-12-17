import logging
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.vendor_api.repository import VendorAccountRepository
from src.core.config import settings
from src.core.database import get_session

from .services.auth_service import MySkladAuthService, build_ms_auth_service

logger = logging.getLogger(__name__)


async def get_ms_auth_service(
    request: Request,
    account_header_id: str | None = Header(default=None, alias="X-Account-Id"),
    session: AsyncSession = Depends(get_session),
) -> MySkladAuthService:
    """Загрузить auth-контекст для конкретного аккаунта.

    Приоритет получения account_id:
    1. X-Account-Id header (явное указание от клиента)
    2. request.state.ms_account_id (из webhook payload)
    3. Единственный активный аккаунт (только если установлена одна компания)
    
    Если установлено 2+ компаний, требуется явное указание account_id.
    """
    auth_service = build_ms_auth_service()
    repo = VendorAccountRepository(session)
    
    resolved_account_id = account_header_id or getattr(
        request.state, "ms_account_id", None
    )

    if not resolved_account_id:
        active_accounts = await repo.list_active_accounts(limit=2)
        
        if len(active_accounts) == 0:
            logger.warning("Попытка доступа без активных аккаунтов")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "No active accounts found. "
                    "Please activate the app via Vendor API first."
                ),
            )
        elif len(active_accounts) == 1:
            resolved_account_id = active_accounts[0].account_id
            logger.debug(
                "Использован единственный активный аккаунт: account_id=%s",
                resolved_account_id,
            )
        else:
            logger.warning(
                "Множественные активные аккаунты (%d), требуется X-Account-Id",
                len(active_accounts),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Multiple active accounts found. "
                    "Please provide X-Account-Id header to specify which account to use."
                ),
            )

    account = await repo.get_by_account_id(resolved_account_id)

    if not account or not account.is_active or not account.access_token:
        logger.warning(
            "Аккаунт не найден или неактивен: account_id=%s",
            resolved_account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account '{resolved_account_id}' is not activated. Please re-run app activation.",
        )

    auth_service.set_access_token(
        account.access_token,
        base_url=settings.ms_base_url,
        account_id=account.account_id,
    )

    logger.debug(
        "Auth контекст загружен: account_id=%s, url=%s, path=%s",
        account.account_id,
        request.url.path,
        request.method,
    )

    return auth_service


AuthSvcDep = Annotated[MySkladAuthService, Depends(get_ms_auth_service)]


async def get_ms_auth_service_for_account(
    account_id: str, session: AsyncSession = Depends(get_session)
) -> MySkladAuthService:
    """Загрузить auth-контекст строго для указанного account_id.

    Используется в вендорских эндпоинтах, где account_id передаётся в path и
    нужно исключить привязку к "дефолтному" аккаунту при мультитенантной работе.
    """
    auth_service = build_ms_auth_service()
    repo = VendorAccountRepository(session)
    account = await repo.get_by_account_id(account_id)

    if not account or not account.is_active or not account.access_token:
        logger.warning(
            "Vendor API: аккаунт не найден или неактивен: account_id=%s",
            account_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Account is not activated or missing access token. "
                "Please re-run app activation."
            ),
        )

    auth_service.set_access_token(
        account.access_token,
        base_url=settings.ms_base_url,
        account_id=account.account_id,
    )

    logger.info(
        "Vendor API: Auth контекст загружен для account_id=%s",
        account.account_id,
    )

    return auth_service