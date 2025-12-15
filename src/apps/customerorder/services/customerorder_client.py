"""Клиент для работы с API заказов покупателя МойСклад."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import CustomerOrderAPIError

logger = logging.getLogger(__name__)


class CustomerOrderClient:
    """
    Клиент для работы с API заказов покупателя МойСклад.
    """
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        """
        Инициализировать клиент.
        
        Args:
            auth_service: Сервис аутентификации
        """
        self._auth_service = auth_service
        self._timeout = 30.0
    
    def _get_base_url(self) -> str:
        """
        Получить базовый URL API.
        
        Returns:
            Базовый URL
            
        Raises:
            CustomerOrderAPIError: Если credentials не настроены
        """
        creds = self._auth_service.get_raw_credentials()
        if not creds:
            raise CustomerOrderAPIError("МойСклад credentials не настроены")
        return str(creds.base_url).rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Получить заголовки для запросов.
        
        Returns:
            Словарь заголовков
            
        Raises:
            CustomerOrderAPIError: Если не удается построить заголовок авторизации
        """
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise CustomerOrderAPIError("Невозможно построить Authorization header")
        
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
    async def get_by_id(self, order_id: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """
        Получить заказ покупателя по ID.
        
        Args:
            order_id: ID заказа в МойСклад
            expand: Дополнительные поля для раскрытия
            
        Returns:
            Данные заказа
            
        Raises:
            CustomerOrderAPIError: При ошибке запроса
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            params = {}
            if expand:
                params["expand"] = expand
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/customerorder/{order_id}"
                logger.debug("Запрос заказа покупателя: %s", order_id)
                
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Получен заказ: %s", data.get("name"))
                return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise CustomerOrderAPIError(
                    f"Заказ {order_id} не найден",
                    details={"order_id": order_id}
                ) from exc
            raise CustomerOrderAPIError(
                "Ошибка HTTP при получении заказа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomerOrderAPIError(
                "Ошибка при получении заказа",
                details={"error": str(exc)},
            ) from exc
    
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
        """
        Поиск заказов покупателя по фильтру.
        
        Args:
            filter_str: Строка фильтра МойСклад
            limit: Максимальное количество записей
            offset: Смещение
            order: Поле для сортировки
            
        Returns:
            Список заказов
            
        Raises:
            CustomerOrderAPIError: При ошибке запроса
        """
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
                url = f"{base_url}/entity/customerorder"
                logger.debug("Поиск заказов с фильтром: %s", filter_str)

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                rows = data.get("rows", [])
                logger.debug("Найдено заказов: %d", len(rows))
                return rows
        except httpx.HTTPStatusError as exc:
            raise CustomerOrderAPIError(
                "Ошибка HTTP при поиске заказов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise CustomerOrderAPIError(
                "Ошибка при поиске заказов",
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
        """
        Поиск заказов по контрагенту и сумме.
        
        Args:
            agent_id: ID контрагента
            sum_value: Сумма для поиска
            tolerance: Допустимая погрешность суммы
            prioritize_oldest: Приоритет старых (True) или новых (False) документов

        Returns:
            Список заказов
        """
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
        only_unpaid: bool = True,
        date_from: Optional[datetime] = None,
        limit: int = 100,
        order: str = "moment,asc",
    ) -> List[Dict[str, Any]]:
        """
        Поиск заказов по контрагенту.

        Args:
            agent_id: ID контрагента
            only_unpaid: Искать только неоплаченные
            date_from: Минимальная дата документа
            limit: Количество документов
            order: Порядок сортировки
        Returns:
            Список заказов
        """
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
        """Получить статусы заказов покупателя."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/customerorder/metadata"
                resp = await client.get(url)
                resp.raise_for_status()

                data = resp.json()
                return data.get("states", [])
        except httpx.HTTPStatusError as exc:
            raise CustomerOrderAPIError(
                "Ошибка HTTP при получении статусов заказов",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover - сетевые ошибки
            raise CustomerOrderAPIError(
                "Ошибка при получении статусов заказов",
                details={"error": str(exc)},
            ) from exc

    async def update_state(self, order_id: str, state_id: str) -> Dict[str, Any]:
        """Установить статус заказа покупателя."""

        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            state_href = f"{base_url}/entity/customerorder/metadata/states/{state_id}"

            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/customerorder/{order_id}"
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
            raise CustomerOrderAPIError(
                "Ошибка HTTP при обновлении статуса заказа",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:  # pragma: no cover
            raise CustomerOrderAPIError(
                "Ошибка при обновлении статуса заказа",
                details={"error": str(exc)},
            ) from exc
