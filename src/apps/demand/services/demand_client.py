"""Клиент для работы с API отгрузок (demand) МойСклад."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import DemandAPIError

logger = logging.getLogger(__name__)


class DemandClient:
    """Клиент для работы с API отгрузок (demand) МойСклад."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = 30.0

    def _get_base_url(self) -> str:
        """Получить базовый URL API."""

        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise DemandAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов."""

        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise DemandAPIError("Невозможно построить Authorization header")

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
        """Поиск отгрузок по фильтру."""

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
                url = f"{base_url}/entity/demand"
                logger.debug("Поиск отгрузок с фильтром: %s", filter_str)

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                rows = data.get("rows", [])
                logger.debug("Найдено отгрузок: %d", len(rows))
                return rows
        except httpx.HTTPStatusError as exc:
            raise DemandAPIError(
                "Ошибка HTTP при поиске отгрузок",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise DemandAPIError(
                "Ошибка при поиске отгрузок",
                details={"error": str(exc)},
            ) from exc

    async def search_by_agent_and_sum(
        self,
        agent_id: str,
        sum_value: float,
        tolerance: float = 0.01,
        prioritize_oldest: bool = True,
    ) -> List[Dict[str, Any]]:
        """Поиск отгрузок по контрагенту и сумме."""

        sum_min = sum_value - tolerance
        sum_max = sum_value + tolerance

        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
            f"sum>={sum_min}",
            f"sum<={sum_max}",
        ]

        filter_str = ";".join(filter_parts)
        order = "moment,asc" if prioritize_oldest else "moment,desc"

        return await self.search(filter_str=filter_str, order=order)

    async def search_by_agent(
        self,
        agent_id: str,
        date_from: Optional[datetime] = None,
        limit: int = 100,
        order: str = "moment,asc"
    ) -> List[Dict[str, Any]]:
        """Поиск отгрузок по контрагенту."""

        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
        ]

        if date_from:
            # МойСклад работает в MSK (UTC+3)
            # Формат: ГГГГ-ММ-ДД ЧЧ:мм:сс (пробел между датой и временем, без T)
            msk_tz = timezone(timedelta(hours=3))
            date_msk = date_from.astimezone(msk_tz)
            # Убираем секунды для совместимости (можно использовать и с секундами)
            filter_parts.append(f"moment>={date_msk.strftime('%Y-%m-%d %H:%M:%S')}")

        filter_str = ";".join(filter_parts)
        return await self.search(filter_str=filter_str, order=order, limit=limit)

    async def get_states(self) -> List[Dict[str, Any]]:
        """Получить статусы отгрузок."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/demand/metadata"
                resp = await client.get(url)
                resp.raise_for_status()

                data = resp.json()
                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise DemandAPIError(
                "Ошибка HTTP при получении статусов отгрузок",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise DemandAPIError(
                "Ошибка при получении статусов отгрузок",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, demand_id: str, state_id: str) -> Dict[str, Any]:
        """Установить статус отгрузки."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/demand/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/demand/{demand_id}"
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
            raise DemandAPIError(
                "Ошибка HTTP при обновлении статуса отгрузки",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise DemandAPIError(
                "Ошибка при обновлении статуса отгрузки",
                details={"error": str(exc)},
            ) from exc
