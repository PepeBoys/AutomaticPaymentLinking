"""Обработчики исключений для cashin."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import CashInAPIError, CashInBaseException, CashInNotFoundError

logger = logging.getLogger(__name__)


async def cashin_not_found_handler(
    request: Request,
    exc: CashInNotFoundError,
) -> JSONResponse:
    """Обработчик для CashInNotFoundError."""
    logger.warning("CashInNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "CashInNotFoundError",
            "details": exc.details,
        },
    )


async def cashin_api_error_handler(
    request: Request,
    exc: CashInAPIError,
) -> JSONResponse:
    """Обработчик для CashInAPIError."""
    logger.error("CashInAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "CashInAPIError",
            "details": exc.details,
        },
    )


async def cashin_base_exception_handler(
    request: Request,
    exc: CashInBaseException,
) -> JSONResponse:
    """Обработчик для CashInBaseException."""
    logger.error(
        "CashInBaseException: %s, details=%s",
        exc.message,
        exc.details,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            "error_type": exc.__class__.__name__,
            "details": exc.details,
        },
    )


EXCEPTION_HANDLERS = {
    CashInNotFoundError: cashin_not_found_handler,
    CashInAPIError: cashin_api_error_handler,
    CashInBaseException: cashin_base_exception_handler,
}