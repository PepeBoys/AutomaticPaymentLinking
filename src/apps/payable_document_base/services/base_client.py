"""Базовый клиент для оплачиваемых документов."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import DocumentAPIError

logger = logging.getLogger(__name__)


class BaseDocumentClient(ABC):
    """Общая логика взаимодействия с API документов."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = 30.0

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Тип сущности (invoicein/invoiceout/...)."""

    def _get_base_url(self) -> str:
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise DocumentAPIError("МойСклад credentials не настроены") from exc

    def _get_headers(self) -> Dict[str, str]:
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise DocumentAPIError("Невозможно построить Authorization header")

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
    async def search(
        self,
        filter_str: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Поиск документов по фильтру."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            params = {
                "limit": min(limit, 1000),
                "offset": offset,
            }

            if filter_str:
                params["filter"] = filter_str

            if order:
                params["order"] = order

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}"
                logger.debug("Поиск документов с фильтром: %s", filter_str)

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                rows = data.get("rows", [])
                logger.debug("Найдено документов: %d", len(rows))
                return rows
        except httpx.HTTPStatusError as exc:
            raise DocumentAPIError(
                "Ошибка HTTP при поиске документов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise DocumentAPIError(
                "Ошибка при поиске документов",
                details={"error": str(exc)},
            ) from exc

    async def search_by_agent_and_sum(
        self,
        agent_id: str,
        sum_value: float,
        tolerance: float = 0.01,
        organization_id: str | None = None,
        prioritize_oldest: bool = True,
    ) -> List[Dict[str, Any]]:
        """Поиск документов по контрагенту и сумме."""
        sum_min = sum_value - tolerance
        sum_max = sum_value + tolerance

        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
            f"sum>={sum_min}",
            f"sum<={sum_max}",
        ]

        if organization_id:
            filter_parts.append(
                "organization=https://api.moysklad.ru/api/remap/1.2/entity/organization/"
                f"{organization_id}"
            )

        filter_str = ";".join(filter_parts)
        order = "moment,asc" if prioritize_oldest else "moment,desc"

        return await self.search(filter_str=filter_str, order=order)

    async def search_by_agent(
        self,
        agent_id: str,
        organization_id: str | None = None,
        date_from: Optional[datetime] = None,
        limit: int = 100,
        order: Optional[str] = None,
        only_unpaid: bool = False,
    ) -> List[Dict[str, Any]]:
        """Поиск документов по контрагенту."""
        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
        ]

        if organization_id:
            filter_parts.append(
                "organization=https://api.moysklad.ru/api/remap/1.2/entity/organization/"
                f"{organization_id}"
            )

        if date_from:
            msk_tz = timezone(timedelta(hours=3))
            date_msk = date_from.astimezone(msk_tz)
            filter_parts.append(
                f"moment>={date_msk.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        if only_unpaid:
            filter_parts.append("payedSum<sum")

        filter_str = ";".join(filter_parts)

        return await self.search(
            filter_str=filter_str,
            limit=limit,
            order=order,
        )

    async def get_states(self) -> list[Dict[str, Any]]:
        """Получить статусы документов."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/metadata"
                logger.debug("Запрос статусов документов")

                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise DocumentAPIError(
                "Ошибка HTTP при получении статусов документов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise DocumentAPIError(
                "Ошибка при получении статусов документов",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, document_id: str, state_id: str) -> Dict[str, Any]:
        """Обновить статус документа."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/{self.entity_type}/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{document_id}"
                logger.debug("Обновление статуса документа: %s -> %s", document_id, state_id)

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
            raise DocumentAPIError(
                "Ошибка HTTP при обновлении статуса документа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # сетевые ошибки
            raise DocumentAPIError(
                "Ошибка при обновлении статуса документа",
                details={"error": str(exc)},
            ) from exc

    async def get_by_id(self, document_id: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """Получить документ по ID."""
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            params = {"expand": expand} if expand else None

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/{self.entity_type}/{document_id}"
                logger.debug("Получение документа: %s", document_id)

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise DocumentAPIError(
                "Ошибка HTTP при получении документа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise DocumentAPIError(
                "Ошибка при получении документа",
                details={"error": str(exc)},
            ) from exc
