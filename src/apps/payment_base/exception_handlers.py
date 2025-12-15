"""Обработчики базовых исключений платежей."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import BasePaymentException, PaymentAPIError, PaymentNotFoundError

logger = logging.getLogger(__name__)


async def payment_not_found_handler(
    request: Request, exc: PaymentNotFoundError
) -> JSONResponse:
    """Обработчик PaymentNotFoundError."""
    logger.warning("PaymentNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "PaymentNotFoundError",
            "details": exc.details,
        },
    )


async def payment_api_error_handler(
    request: Request, exc: PaymentAPIError
) -> JSONResponse:
    """Обработчик PaymentAPIError."""
    logger.error("PaymentAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "PaymentAPIError",
            "details": exc.details,
        },
    )


async def base_payment_exception_handler(
    request: Request, exc: BasePaymentException
) -> JSONResponse:
    """Обработчик BasePaymentException."""
    logger.error(
        "BasePaymentException: %s, details=%s", exc.message, exc.details
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": exc.message,
            "error_type": exc.__class__.__name__,
            "details": exc.details,
        },
    )


BASE_EXCEPTION_HANDLERS = {
    PaymentNotFoundError: payment_not_found_handler,
    PaymentAPIError: payment_api_error_handler,
    BasePaymentException: base_payment_exception_handler,
}
