"""Клиент для работы с API счетов покупателю МойСклад."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import InvoiceOutAPIError

logger = logging.getLogger(__name__)


class InvoiceOutClient:
    """Клиент для работы с API счетов покупателю МойСклад."""

    def __init__(self, auth_service: MySkladAuthService) -> None:
        self._auth_service = auth_service
        self._timeout = 30.0

    def _get_base_url(self) -> str:
        """Получить базовый URL API."""
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise InvoiceOutAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запросов."""
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise InvoiceOutAPIError("Невозможно построить Authorization header")

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
        """Поиск счетов покупателю по фильтру."""
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
                url = f"{base_url}/entity/invoiceout"
                logger.debug("Поиск счетов с фильтром: %s", filter_str)

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                rows = data.get("rows", [])
                logger.debug("Найдено счетов: %d", len(rows))
                return rows
        except httpx.HTTPStatusError as exc:
            raise InvoiceOutAPIError(
                "Ошибка HTTP при поиске счетов покупателю",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise InvoiceOutAPIError(
                "Ошибка при поиске счетов покупателю",
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
        """Поиск счетов по контрагенту и сумме."""
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
        order: str = "moment,asc",
    ) -> List[Dict[str, Any]]:
        """Поиск счетов по контрагенту."""
        filter_parts = [
            f"agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/{agent_id}",
        ]

        if organization_id:
            filter_parts.append(
                "organization=https://api.moysklad.ru/api/remap/1.2/entity/organization/"
                f"{organization_id}"
            )

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
        """Получить статусы счетов покупателю."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/invoiceout/metadata"
                resp = await client.get(url)
                resp.raise_for_status()

                data = resp.json()
                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise InvoiceOutAPIError(
                "Ошибка HTTP при получении статусов счетов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise InvoiceOutAPIError(
                "Ошибка при получении статусов счетов",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, invoice_id: str, state_id: str) -> Dict[str, Any]:
        """Установить статус счета покупателю."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/invoiceout/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/invoiceout/{invoice_id}"
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
            raise InvoiceOutAPIError(
                "Ошибка HTTP при обновлении статуса счета",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise InvoiceOutAPIError(
                "Ошибка при обновлении статуса счета",
                details={"error": str(exc)},
            ) from exc
