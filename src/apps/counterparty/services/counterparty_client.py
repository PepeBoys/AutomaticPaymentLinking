"""Клиент для работы с API контрагентов (counterparty) МойСклад."""

import logging
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import CounterpartyAPIError, CounterpartyNotFoundError

logger = logging.getLogger(__name__)
RETRY_ATTEMPTS = settings.webhook_retry_attempts


class CounterpartyClient:
    """Клиент для работы с API контрагентов."""

    entity_type = "counterparty"

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = settings.webhook_timeout

    def _get_base_url(self) -> str:
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise CounterpartyAPIError("МойСклад credentials не настроены") from exc

    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise CounterpartyAPIError("Невозможно построить Authorization header")

        return {
            **auth_header,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_by_id(self, agent_id: str) -> Dict[str, Any]:
        """Получить контрагента по ID."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{agent_id}"
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CounterpartyNotFoundError(
                    f"Контрагент не найден: {agent_id}",
                    details={"id": agent_id},
                ) from exc
            raise CounterpartyAPIError(
                "Ошибка HTTP при получении контрагента",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except CounterpartyNotFoundError:
            raise
        except Exception as exc:
            raise CounterpartyAPIError(
                "Ошибка при получении контрагента",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_metadata(self) -> Dict[str, Any]:
        """Получить метаданные контрагента (включая описание доп. полей)."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/metadata"
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CounterpartyAPIError(
                "Ошибка HTTP при получении метаданных контрагента",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CounterpartyAPIError(
                "Ошибка при получении метаданных контрагента",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create_attribute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Создать доп. поле (атрибут метаданных) контрагента."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/metadata/attributes"
                logger.info("Создание доп. поля контрагента: %s", payload.get("name"))
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CounterpartyAPIError(
                "Ошибка HTTP при создании доп. поля контрагента",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CounterpartyAPIError(
                "Ошибка при создании доп. поля контрагента",
                details={"error": str(exc)},
            ) from exc
