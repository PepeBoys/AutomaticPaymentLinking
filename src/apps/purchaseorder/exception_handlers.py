"""Обработчики исключений для purchaseorder."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import (
    PurchaseOrderAPIError,
    PurchaseOrderBaseException,
    PurchaseOrderNotFoundError,
)

logger = logging.getLogger(__name__)


async def purchaseorder_not_found_handler(
    request: Request,
    exc: PurchaseOrderNotFoundError,
) -> JSONResponse:
    """Обработчик для PurchaseOrderNotFoundError."""
    logger.warning("PurchaseOrderNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "PurchaseOrderNotFoundError",
            "details": exc.details,
        },
    )


async def purchaseorder_api_error_handler(
    request: Request,
    exc: PurchaseOrderAPIError,
) -> JSONResponse:
    """Обработчик для PurchaseOrderAPIError."""
    logger.error("PurchaseOrderAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "PurchaseOrderAPIError",
            "details": exc.details,
        },
    )


async def purchaseorder_base_exception_handler(
    request: Request,
    exc: PurchaseOrderBaseException,
) -> JSONResponse:
    """Обработчик для PurchaseOrderBaseException."""
    logger.error(
        "PurchaseOrderBaseException: %s, details=%s",
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
    PurchaseOrderNotFoundError: purchaseorder_not_found_handler,
    PurchaseOrderAPIError: purchaseorder_api_error_handler,
    PurchaseOrderBaseException: purchaseorder_base_exception_handler,
}