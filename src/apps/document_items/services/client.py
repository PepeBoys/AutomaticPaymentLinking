"""Клиент JSON API МойСклад: документы и их доп. поля в сыром виде."""

import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import DocumentItemsAPIError

logger = logging.getLogger(__name__)
RETRY_ATTEMPTS = settings.webhook_retry_attempts


class DocumentItemsClient:
    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = settings.webhook_timeout

    def base_url(self) -> str:
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise DocumentItemsAPIError("МойСклад credentials не настроены") from exc

    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise DocumentItemsAPIError("Невозможно построить Authorization header")
        return {
            **auth_header,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                headers=self._get_headers(), timeout=self._timeout
            ) as client:
                return await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise DocumentItemsAPIError(
                f"Ошибка сети при {method} {url}", details={"error": str(exc)}
            ) from exc

    @staticmethod
    def _check(resp: httpx.Response, action: str) -> Dict[str, Any]:
        if resp.status_code >= 400:
            raise DocumentItemsAPIError(
                f"Ошибка HTTP при {action}",
                details={"status_code": resp.status_code, "response": resp.text[:1000]},
            )
        return resp.json()

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def list_attributes(self, entity_type: str) -> list[Dict[str, Any]]:
        url = f"{self.base_url()}/entity/{entity_type}/metadata/attributes"
        data = self._check(await self._request("GET", url), f"получении доп. полей {entity_type}")
        return data if isinstance(data, list) else data.get("rows", [])

    async def create_attribute(self, entity_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Создать доп. поле. Без ретрая: создание не идемпотентно."""
        url = f"{self.base_url()}/entity/{entity_type}/metadata/attributes"
        logger.info("Создание доп. поля %s: %s", entity_type, payload.get("name"))
        return self._check(
            await self._request("POST", url, json=payload),
            f"создании доп. поля {entity_type}",
        )

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_by_href(self, href: str) -> Optional[Dict[str, Any]]:
        """Документ/сущность по href или None, если удалён (404)."""
        resp = await self._request("GET", href)
        if resp.status_code == 404:
            return None
        return self._check(resp, f"получении {href}")

    async def set_customentity_attribute(
        self, entity_type: str, document_id: str, attribute_id: str, element_href: str
    ) -> Dict[str, Any]:
        """Записать в доп. поле «справочник» документа ссылку на элемент справочника."""
        base_url = self.base_url()
        payload = {
            "attributes": [
                {
                    "meta": {
                        "href": f"{base_url}/entity/{entity_type}/metadata/attributes/{attribute_id}",
                        "type": "attributemetadata",
                        "mediaType": "application/json",
                    },
                    "value": {
                        "meta": {
                            "href": element_href,
                            "type": "customentity",
                            "mediaType": "application/json",
                        }
                    },
                }
            ]
        }
        url = f"{base_url}/entity/{entity_type}/{document_id}"
        return self._check(
            await self._request("PUT", url, json=payload),
            f"обновлении доп. поля {entity_type} {document_id}",
        )
