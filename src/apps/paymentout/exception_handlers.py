"""Обработчики исключений для paymentout."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    PaymentOutAPIError,
    PaymentOutBaseException,
    PaymentOutNotFoundError,
)

logger = logging.getLogger(__name__)


async def paymentout_not_found_handler(
    request: Request,
    exc: PaymentOutNotFoundError,
) -> JSONResponse:
    """Обработчик для PaymentOutNotFoundError."""
    logger.warning("PaymentOutNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "PaymentOutNotFoundError",
            "details": exc.details,
        },
    )


async def paymentout_api_error_handler(
    request: Request,
    exc: PaymentOutAPIError,
) -> JSONResponse:
    """Обработчик для PaymentOutAPIError."""
    logger.error("PaymentOutAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "PaymentOutAPIError",
            "details": exc.details,
        },
    )


async def paymentout_base_exception_handler(
    request: Request,
    exc: PaymentOutBaseException,
) -> JSONResponse:
    """Обработчик для PaymentOutBaseException."""
    logger.error(
        "PaymentOutBaseException: %s, details=%s",
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
    PaymentOutNotFoundError: paymentout_not_found_handler,
    PaymentOutAPIError: paymentout_api_error_handler,
    PaymentOutBaseException: paymentout_base_exception_handler,
}