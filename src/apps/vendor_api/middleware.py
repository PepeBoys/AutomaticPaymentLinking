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
    
    Используется для запросов из браузера, где МойСклад передаёт appUid,
    но не передаёт X-Account-Id заголовок.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Если account_id уже установлен (например, из вебхука) - пропускаем
        if hasattr(request.state, "ms_account_id") and request.state.ms_account_id:
            return await call_next(request)

        # Проверяем наличие appUid в query параметрах
        app_uid = request.query_params.get("appUid")
        if not app_uid:
            return await call_next(request)

        # Ищем активный аккаунт по app_uid в БД
        try:
            async with async_session_maker() as session:
                stmt = (
                    select(VendorAccount)
                    .where(VendorAccount.app_uid == app_uid)
                    .where(VendorAccount.is_active.is_(True))
                )
                result = await session.execute(stmt)
                account = result.scalar_one_or_none()

                if account:
                    request.state.ms_account_id = account.account_id
                    logger.debug(
                        "Account ID установлен из appUid: %s -> %s",
                        app_uid,
                        account.account_id,
                    )
                else:
                    logger.warning(
                        "Активный аккаунт не найден для appUid=%s",
                        app_uid,
                    )
        except Exception as e:
            logger.error(
                "Ошибка при извлечении account_id по appUid: %s",
                e,
                exc_info=True,
            )

        return await call_next(request)