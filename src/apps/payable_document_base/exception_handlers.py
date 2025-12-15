"""Обработчики базовых исключений документов."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .exceptions import BaseDocumentException, DocumentAPIError, DocumentNotFoundError

logger = logging.getLogger(__name__)


async def document_not_found_handler(
    request: Request, exc: DocumentNotFoundError
) -> JSONResponse:
    """Обработчик DocumentNotFoundError."""
    logger.warning("DocumentNotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
            "error_type": "DocumentNotFoundError",
            "details": exc.details,
        },
    )


async def document_api_error_handler(
    request: Request, exc: DocumentAPIError
) -> JSONResponse:
    """Обработчик DocumentAPIError."""
    logger.error("DocumentAPIError: %s, details=%s", exc.message, exc.details)
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": f"Ошибка API МойСклад: {exc.message}",
            "error_type": "DocumentAPIError",
            "details": exc.details,
        },
    )


async def base_document_exception_handler(
    request: Request, exc: BaseDocumentException
) -> JSONResponse:
    """Обработчик BaseDocumentException."""
    logger.error(
        "BaseDocumentException: %s, details=%s", exc.message, exc.details
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
    DocumentNotFoundError: document_not_found_handler,
    DocumentAPIError: document_api_error_handler,
    BaseDocumentException: base_document_exception_handler,
}
