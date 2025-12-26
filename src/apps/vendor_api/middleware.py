import logging
from typing import Callable

from fastapi import Request, Response
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.database import async_session_maker

from .models import VendorAccount

logger = logging.getLogger(__name__)


class AppUidAccountMiddleware(BaseHTTPMiddleware):
    """
    Middleware для автоматического определения account_id по appUid из query параметров.
    
    Сохраняет account_id в cookie при первом запросе с appUid,
    затем читает из cookie при последующих запросах.
    """

    COOKIE_NAME = "ms_account_id"
    COOKIE_MAX_AGE = 86400  # 24 часа

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Если account_id уже установлен (например, из вебхука) - пропускаем
        if hasattr(request.state, "ms_account_id") and request.state.ms_account_id:
            return await call_next(request)

        account_id = None

        # 1. Пытаемся получить из appUid (приоритет)
        app_uid = request.query_params.get("appUid")
        if app_uid:
            account_id = await self._get_account_id_by_app_uid(app_uid)
            if account_id:
                logger.debug(
                    "Account ID установлен из appUid: %s -> %s",
                    app_uid,
                    account_id,
                )

        # 2. Если не нашли через appUid, пытаемся прочитать из cookie
        if not account_id:
            account_id = request.cookies.get(self.COOKIE_NAME)
            if account_id:
                logger.debug("Account ID прочитан из cookie: %s", account_id)

        # 3. Устанавливаем в request.state если нашли
        if account_id:
            request.state.ms_account_id = account_id

        # Выполняем запрос
        response = await call_next(request)

        # 4. Если нашли account_id через appUid - сохраняем в cookie
        if app_uid and account_id and isinstance(response, Response):
            response.set_cookie(
                key=self.COOKIE_NAME,
                value=account_id,
                max_age=self.COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
            )
            logger.debug("Account ID сохранен в cookie: %s", account_id)

        return response

    async def _get_account_id_by_app_uid(self, app_uid: str) -> str | None:
        """Найти account_id по app_uid в БД."""
        try:
            async with async_session_maker() as session:
                stmt = (
                    select(VendorAccount.account_id)
                    .where(VendorAccount.app_uid == app_uid)
                    .where(VendorAccount.is_active.is_(True))
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()
                return account
        except Exception as e:
            logger.error(
                "Ошибка при извлечении account_id по appUid=%s: %s",
                app_uid,
                e,
                exc_info=True,
            )
            return None