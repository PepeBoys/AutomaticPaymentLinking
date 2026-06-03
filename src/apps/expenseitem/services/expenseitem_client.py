"""Клиент для работы с API статей расходов (expenseitem) МойСклад."""

import logging
from typing import Any, Dict, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import ExpenseItemAPIError, ExpenseItemNotFoundError

logger = logging.getLogger(__name__)
RETRY_ATTEMPTS = settings.webhook_retry_attempts


class ExpenseItemClient:
    """Клиент для работы с API статей расходов."""

    entity_type = "expenseitem"

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = settings.webhook_timeout

    def _get_base_url(self) -> str:
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise ExpenseItemAPIError("МойСклад credentials не настроены") from exc

    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise ExpenseItemAPIError("Невозможно построить Authorization header")

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
    async def list_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Получить все статьи расходов (с пагинацией)."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            all_rows: list[Dict[str, Any]] = []
            offset = 0

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}"
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

                logger.debug("Получено статей расходов: %d", len(all_rows))
                return all_rows
        except httpx.HTTPStatusError as exc:
            raise ExpenseItemAPIError(
                "Ошибка HTTP при получении статей расходов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise ExpenseItemAPIError(
                "Ошибка при получении статей расходов",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_by_id(self, item_id: str) -> Dict[str, Any]:
        """Получить статью расходов по ID."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{item_id}"
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ExpenseItemNotFoundError(
                    f"Статья расходов не найдена: {item_id}",
                    details={"id": item_id},
                ) from exc
            raise ExpenseItemAPIError(
                "Ошибка HTTP при получении статьи расходов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except ExpenseItemNotFoundError:
            raise
        except Exception as exc:
            raise ExpenseItemAPIError(
                "Ошибка при получении статьи расходов",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Создать статью расходов."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}"
                logger.info("Создание статьи расходов: %s", payload.get("name"))
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise ExpenseItemAPIError(
                "Ошибка HTTP при создании статьи расходов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise ExpenseItemAPIError(
                "Ошибка при создании статьи расходов",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def update(self, item_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить статью расходов."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{item_id}"
                logger.info("Обновление статьи расходов: %s", item_id)
                resp = await client.put(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise ExpenseItemNotFoundError(
                    f"Статья расходов не найдена: {item_id}",
                    details={"id": item_id},
                ) from exc
            raise ExpenseItemAPIError(
                "Ошибка HTTP при обновлении статьи расходов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except ExpenseItemNotFoundError:
            raise
        except Exception as exc:
            raise ExpenseItemAPIError(
                "Ошибка при обновлении статьи расходов",
                details={"error": str(exc)},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def delete(self, item_id: str) -> bool:
        """Удалить статью расходов. Возвращает False, если не найдена."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{item_id}"
                logger.info("Удаление статьи расходов: %s", item_id)
                resp = await client.delete(url)
                resp.raise_for_status()
                return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning("Статья расходов не найдена при удалении: %s", item_id)
                return False
            raise ExpenseItemAPIError(
                "Ошибка HTTP при удалении статьи расходов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise ExpenseItemAPIError(
                "Ошибка при удалении статьи расходов",
                details={"error": str(exc)},
            ) from exc
