"""Клиент для работы с API входящих платежей МойСклад."""

import logging
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import PaymentInAPIError, PaymentInNotFoundError

logger = logging.getLogger(__name__)


class PaymentInClient:
    """Клиент для работы с API входящих платежей МойСклад."""
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = 30.0
    
    def _get_base_url(self) -> str:
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise PaymentInAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise PaymentInAPIError("Невозможно построить Authorization header")
        
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
        """Получить входящий платеж по полному href."""
        try:
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                logger.debug("Запрос входящего платежа по href: %s", href)
                
                resp = await client.get(href)
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Получен платеж: %s", data.get("name"))
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise PaymentInNotFoundError(
                    f"Входящий платеж не найден: {href}",
                    details={"href": href}
                ) from exc
            raise PaymentInAPIError(
                "Ошибка HTTP при получении платежа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise PaymentInAPIError(
                "Ошибка при получении платежа",
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
        """Обновить связи платежа с документами."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/paymentin/{payment_id}"
                logger.debug("Обновление операций платежа: %s", payment_id)
                
                resp = await client.put(url, json={"operations": operations})
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Платеж обновлен: %s", data.get("name"))
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise PaymentInNotFoundError(
                    f"Входящий платеж {payment_id} не найден",
                    details={"payment_id": payment_id}
                ) from exc
            raise PaymentInAPIError(
                "Ошибка HTTP при обновлении платежа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise PaymentInAPIError(
                "Ошибка при обновлении платежа",
                details={"error": str(exc)},
            ) from exc

    async def get_states(self) -> list[Dict[str, Any]]:
        """Получить список статусов для входящих платежей."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/paymentin/metadata"
                logger.debug("Запрос статусов платежей")

                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise PaymentInAPIError(
                "Ошибка HTTP при получении статусов платежей",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise PaymentInAPIError(
                "Ошибка при получении статусов платежей",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, payment_id: str, state_id: str) -> Dict[str, Any]:
        """Обновить статус входящего платежа."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/paymentin/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/paymentin/{payment_id}"
                logger.debug("Обновление статуса платежа: %s -> %s", payment_id, state_id)

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
            raise PaymentInAPIError(
                "Ошибка HTTP при обновлении статуса платежа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # сетевые ошибки
            raise PaymentInAPIError(
                "Ошибка при обновлении статуса платежа",
                details={"error": str(exc)},
            ) from exc

    async def update_project(self, payment_id: str, project_href: str) -> Dict[str, Any]:
        """Обновить проект входящего платежа."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/paymentin/{payment_id}"
                logger.debug(
                    "Обновление проекта платежа: %s -> %s", payment_id, project_href
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
            raise PaymentInAPIError(
                "Ошибка HTTP при обновлении проекта платежа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise PaymentInAPIError(
                "Ошибка при обновлении проекта платежа",
                details={"error": str(exc)},
            ) from exc
