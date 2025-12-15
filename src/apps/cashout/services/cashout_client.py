"""Клиент для работы с API приходных ордеров МойСклад."""

import logging
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import CashOutAPIError, CashOutNotFoundError

logger = logging.getLogger(__name__)


class CashOutClient:
    """Клиент для работы с API приходных ордеров МойСклад."""
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = 30.0
    
    def _get_base_url(self) -> str:
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise CashOutAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise CashOutAPIError("Невозможно построить Authorization header")
        
        return {
            **auth_header,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_by_href(self, href: str) -> Dict[str, Any]:
        """Получить приходный ордер по полному href."""
        try:
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                logger.debug("Запрос приходного ордера по href: %s", href)
                
                resp = await client.get(href)
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Получен приходный ордер: %s", data.get("name"))
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CashOutNotFoundError(
                    f"Приходный ордер не найден: {href}",
                    details={"href": href}
                ) from exc
            raise CashOutAPIError(
                "Ошибка HTTP при получении приходного ордера",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CashOutAPIError(
                "Ошибка при получении приходного ордера",
                details={"error": str(exc)},
            ) from exc
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def update_operations(
        self, payment_id: str, operations: list[dict]
    ) -> Dict[str, Any]:
        """Обновить связи приходного ордера с документами."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/cashout/{payment_id}"
                logger.debug("Обновление операций приходного ордера: %s", payment_id)
                
                resp = await client.put(url, json={"operations": operations})
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Приходный ордер обновлен: %s", data.get("name"))
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CashOutNotFoundError(
                    f"Приходный ордер {payment_id} не найден",
                    details={"payment_id": payment_id}
                ) from exc
            raise CashOutAPIError(
                "Ошибка HTTP при обновлении приходного ордера",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CashOutAPIError(
                "Ошибка при обновлении приходного ордера",
                details={"error": str(exc)},
            ) from exc

    async def get_states(self) -> list[Dict[str, Any]]:
        """Получить список статусов для приходных ордеров."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/cashout/metadata"
                logger.debug("Запрос статусов приходных ордеров")

                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise CashOutAPIError(
                "Ошибка HTTP при получении статусов приходных ордеров",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise CashOutAPIError(
                "Ошибка при получении статусов приходных ордеров",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, payment_id: str, state_id: str) -> Dict[str, Any]:
        """Обновить статус приходного ордера."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/cashout/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/cashout/{payment_id}"
                logger.debug("Обновление статуса приходного ордера: %s -> %s", payment_id, state_id)

                resp = await client.put(
                    url,
                    json={
                        "state": {
                            "meta": {
                                "href": state_href,
                                "type": "state",
                                "mediaType": "application/json",
                            }
                        }
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CashOutAPIError(
                "Ошибка HTTP при обновлении статуса приходного ордера",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # сетевые ошибки
            raise CashOutAPIError(
                "Ошибка при обновлении статуса приходного ордера",
                details={"error": str(exc)},
            ) from exc

    async def update_project(self, payment_id: str, project_href: str) -> Dict[str, Any]:
        """Обновить проект приходного ордера."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/cashout/{payment_id}"
                logger.debug(
                    "Обновление проекта приходного ордера: %s -> %s", payment_id, project_href
                )

                payload = {
                    "project": {
                        "meta": {
                            "href": project_href,
                            "type": "project",
                            "mediaType": "application/json",
                        }
                    }
                }

                resp = await client.put(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise CashOutAPIError(
                "Ошибка HTTP при обновлении проекта приходного ордера",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise CashOutAPIError(
                "Ошибка при обновлении проекта приходного ордера",
                details={"error": str(exc)},
            ) from exc
