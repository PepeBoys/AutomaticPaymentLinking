"""Клиент для работы с API пользовательских справочников (customentity)."""

import logging
from typing import Any, Dict, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import CustomEntityAPIError, CustomEntityNotFoundError

logger = logging.getLogger(__name__)
RETRY_ATTEMPTS = settings.webhook_retry_attempts


class CustomEntityClient:
    """Клиент для работы с API пользовательских справочников.

    Различаем два уровня:
    - сам справочник (customentity) — идентифицируется metadata_id;
    - элементы справочника — живут под /entity/customentity/{metadata_id}.
    """

    entity_type = "customentity"

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = settings.webhook_timeout

    def _get_base_url(self) -> str:
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise CustomEntityAPIError("МойСклад credentials не настроены") from exc

    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise CustomEntityAPIError("Невозможно построить Authorization header")

        return {
            **auth_header,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

    # ----- Справочник (метаданные) -----

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create_dictionary(self, name: str) -> Dict[str, Any]:
        """Создать новый пользовательский справочник."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}"
                logger.info("Создание пользовательского справочника: %s", name)
                resp = await client.post(url, json={"name": name})
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CustomEntityAPIError(
                "Ошибка HTTP при создании справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при создании справочника",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_metadata(self, metadata_id: str) -> Dict[str, Any]:
        """Получить метаданные справочника."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}/metadata"
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CustomEntityNotFoundError(
                    f"Справочник не найден: {metadata_id}",
                    details={"metadata_id": metadata_id},
                ) from exc
            raise CustomEntityAPIError(
                "Ошибка HTTP при получении метаданных справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except CustomEntityNotFoundError:
            raise
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при получении метаданных справочника",
                details={"error": str(exc)},
            ) from exc

    # ----- Элементы справочника -----

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def list_elements(
        self, metadata_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Получить все элементы справочника (с пагинацией)."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            all_rows: list[Dict[str, Any]] = []
            offset = 0

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}"
                while True:
                    resp = await client.get(url, params={"limit": limit, "offset": offset})
                    resp.raise_for_status()
                    data = resp.json()

                    rows = data.get("rows", [])
                    all_rows.extend(rows)

                    total_size = data.get("meta", {}).get("size")
                    if total_size is None:
                        if len(rows) < limit:
                            break
                        offset += limit
                        continue

                    offset += limit
                    if offset >= total_size:
                        break

                logger.debug(
                    "Получено элементов справочника %s: %d", metadata_id, len(all_rows)
                )
                return all_rows
        except httpx.HTTPStatusError as exc:
            raise CustomEntityAPIError(
                "Ошибка HTTP при получении элементов справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при получении элементов справочника",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_element(self, metadata_id: str, element_id: str) -> Dict[str, Any]:
        """Получить элемент справочника по ID."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}/{element_id}"
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CustomEntityNotFoundError(
                    f"Элемент справочника не найден: {element_id}",
                    details={"metadata_id": metadata_id, "element_id": element_id},
                ) from exc
            raise CustomEntityAPIError(
                "Ошибка HTTP при получении элемента справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except CustomEntityNotFoundError:
            raise
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при получении элемента справочника",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create_element(
        self, metadata_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Создать элемент справочника."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}"
                logger.info(
                    "Создание элемента справочника %s: %s",
                    metadata_id,
                    payload.get("name"),
                )
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CustomEntityAPIError(
                "Ошибка HTTP при создании элемента справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при создании элемента справочника",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def update_element(
        self, metadata_id: str, element_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Обновить элемент справочника."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}/{element_id}"
                logger.info("Обновление элемента справочника %s: %s", metadata_id, element_id)
                resp = await client.put(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CustomEntityNotFoundError(
                    f"Элемент справочника не найден: {element_id}",
                    details={"metadata_id": metadata_id, "element_id": element_id},
                ) from exc
            raise CustomEntityAPIError(
                "Ошибка HTTP при обновлении элемента справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except CustomEntityNotFoundError:
            raise
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при обновлении элемента справочника",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def delete_element(self, metadata_id: str, element_id: str) -> bool:
        """Удалить элемент справочника. Возвращает False, если не найден."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{metadata_id}/{element_id}"
                logger.info("Удаление элемента справочника %s: %s", metadata_id, element_id)
                resp = await client.delete(url)
                resp.raise_for_status()
                return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning("Элемент справочника не найден при удалении: %s", element_id)
                return False
            raise CustomEntityAPIError(
                "Ошибка HTTP при удалении элемента справочника",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomEntityAPIError(
                "Ошибка при удалении элемента справочника",
                details={"error": str(exc)},
            ) from exc
