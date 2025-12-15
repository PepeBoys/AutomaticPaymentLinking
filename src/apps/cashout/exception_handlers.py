"""Обработчики исключений для cashout."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import CashOutAPIError, CashOutBaseException, CashOutNotFoundError

logger = logging.getLogger(__name__)


async def cashout_not_found_handler(
    request: Request,
    exc: CashOutNotFoundError,
) -> JSONResponse:
    """Обработчик для CashOutNotFoundError."""
    logger.warning("CashOutNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "CashOutNotFoundError",
            "details": exc.details,
        },
    )


async def cashout_api_error_handler(
    request: Request,
    exc: CashOutAPIError,
) -> JSONResponse:
    """Обработчик для CashOutAPIError."""
    logger.error("CashOutAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "CashOutAPIError",
            "details": exc.details,
        },
    )


async def cashout_base_exception_handler(
    request: Request,
    exc: CashOutBaseException,
) -> JSONResponse:
    """Обработчик для CashOutBaseException."""
    logger.error(
        "CashOutBaseException: %s, details=%s",
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
    CashOutNotFoundError: cashout_not_found_handler,
    CashOutAPIError: cashout_api_error_handler,
    CashOutBaseException: cashout_base_exception_handler,
}