"""Клиент для взаимодействия с API МойСклад."""

import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...ms_auth.services.auth_service import MySkladAuthService
from ..exceptions import MoySkladAPIError

logger = logging.getLogger(__name__)


class MoySkladClient:
    """
    Клиент для работы с API МойСклад.
    
    Инкапсулирует логику HTTP-запросов к API.
    """
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        """
        Инициализировать клиент МойСклад.
        
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
            MoySkladAPIError: Если credentials не настроены
        """
        try:
            return self._auth_service.get_base_url()
        except Exception as exc:
            raise MoySkladAPIError("МойСклад credentials не настроены") from exc
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Получить заголовки для запросов.
        
        Returns:
            Словарь заголовков
            
        Raises:
            MoySkladAPIError: Если не удается построить заголовок авторизации
        """
        auth_header = self._auth_service.get_basic_auth_header()
        if not auth_header:
            raise MoySkladAPIError("Невозможно построить Authorization header")
        
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
    async def list_webhooks(self, limit: int = 100) -> list[Dict[str, Any]]:
        """
        Получить список вебхуков.
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            Список вебхуков
            
        Raises:
            MoySkladAPIError: При ошибке запроса
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            all_rows: list[Dict[str, Any]] = []
            offset = 0
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/webhook"
                while True:
                    logger.debug(
                        "Запрос списка вебхуков: %s (limit=%s, offset=%s)",
                        url,
                        limit,
                        offset,
                    )
                    resp = await client.get(url, params={"limit": limit, "offset": offset})
                    resp.raise_for_status()
                    data = resp.json()

                    rows = data.get("rows", [])
                    all_rows.extend(rows)
                    logger.info("Получено вебхуков в пакете: %d (всего: %d)", len(rows), len(all_rows))

                    for webhook in rows:
                        logger.info(
                            "Найден вебхук в МойСклад: id=%s, entityType=%s, action=%s, url=%s, enabled=%s",
                            webhook.get("id"),
                            webhook.get("entityType"),
                            webhook.get("action"),
                            webhook.get("url"),
                            webhook.get("enabled"),
                        )

                    meta = data.get("meta", {})
                    total_size = meta.get("size")

                    if total_size is None:
                        # Fallback: если size отсутствует, выходим когда получили меньше лимита
                        if len(rows) < limit:
                            break
                        offset += limit
                        continue

                    offset += limit
                    if offset >= total_size:
                        break

                return all_rows
                
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при получении списка вебхуков",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при получении списка вебхуков",
                details={"error": str(exc)},
            ) from exc
    
    async def get_webhook_by_id(self, webhook_id: str) -> Dict[str, Any]:
        """
        Получить вебхук по ID.
        
        Args:
            webhook_id: ID вебхука
            
        Returns:
            Данные вебхука
            
        Raises:
            MoySkladAPIError: При ошибке запроса
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/webhook/{webhook_id}"
                logger.debug("Запрос вебхука по ID: %s", webhook_id)
                
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                
                logger.debug("Получен вебхук: %s", data.get("id"))
                return data
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при получении вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при получении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    # @retry(
    #     stop=stop_after_attempt(3),
    #     wait=wait_exponential(multiplier=1, min=2, max=10),
    #     reraise=True,
    # )
    async def create_webhook(
        self,
        entity_type: str,
        action: str,
        url: str,
    ) -> Dict[str, Any]:
        """
        Создать новый вебхук.
        
        Args:
            entity_type: Тип сущности
            action: Действие (CREATE, UPDATE, DELETE)
            url: URL для вебхука
            
        Returns:
            Данные созданного вебхука
            
        Raises:
            MoySkladAPIError: При ошибке создания
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            payload = {
                "url": url,
                "action": action,
                "entityType": entity_type,
            }
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                create_url = f"{base_url}/entity/webhook"
                logger.info("Создание вебхука: %s", payload)
                
                resp = await client.post(create_url, json=payload)
                resp.raise_for_status()
                result = resp.json()
                
                logger.info("Вебхук создан: id=%s", result.get("id"))
                return result
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 412:
                logger.warning(
                    "Получен 412 при создании вебхука. Возможно вебхук уже существует. "
                    "Попытка найти существующий..."
                )
                try:
                    error_data = exc.response.json()
                    logger.error("Детали ошибки 412: %s", error_data)
                except Exception:
                    logger.error("Не удалось распарсить тело ответа 412")
                
                # existing = await self.find_webhook_relaxed(entity_type, action)
                # if existing:
                #     logger.info(
                #         "Найден существующий вебхук (relaxed search): id=%s, url=%s, enabled=%s",
                #         existing.get("id"),
                #         existing.get("url"),
                #         existing.get("enabled"),
                #     )
                    
                #     if existing.get("url") != url:
                #         logger.warning(
                #             "URL вебхука отличается! Ожидали: %s, получили: %s",
                #             url,
                #             existing.get("url"),
                #         )
                    
                    # return existing
                
            raise MoySkladAPIError(
                "Ошибка HTTP при создании вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при создании вебхука",
                details={"error": str(exc)},
            ) from exc
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def update_webhook(
        self,
        webhook_data: Dict[str, Any],
        *,
        enabled: bool | None = None,
        url: str | None = None,
    ) -> Dict[str, Any]:
        """
        Обновить параметры вебхука (url и/или статус).
        
        Args:
            webhook_data: Данные вебхука с meta.href
            enabled: Новый статус (если нужно изменить)
            url: Новый url (если нужно изменить)
            
        Returns:
            Обновленные данные вебхука
            
        Raises:
            MoySkladAPIError: При ошибке обновления
        """
        if enabled is None and url is None:
            raise MoySkladAPIError("Не переданы изменяемые параметры вебхука")
        
        try:
            headers = self._get_headers()
            meta = webhook_data.get("meta") or {}
            href = meta.get("href")
            
            if not href:
                webhook_id = webhook_data.get("id")
                raise MoySkladAPIError(
                    f"Отсутствует meta.href для вебхука {webhook_id}"
                )
            
            webhook_id = webhook_data.get("id")
            payload: Dict[str, Any] = {}
            if enabled is not None:
                payload["enabled"] = enabled
            if url is not None:
                payload["url"] = url

            logger.info(
                "Обновление вебхука %s: enabled=%s url=%s",
                webhook_id,
                enabled,
                url,
            )
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                resp = await client.put(href, json=payload)
                resp.raise_for_status()
                result = resp.json()
                
                logger.info(
                    "Вебхук обновлен: id=%s, enabled=%s, url=%s",
                    result.get("id"),
                    result.get("enabled"),
                    result.get("url"),
                )
                return result
        except httpx.HTTPStatusError as exc:
            raise MoySkladAPIError(
                "Ошибка HTTP при обновлении вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при обновлении вебхука",
                details={"error": str(exc)},
            ) from exc
    
    async def find_webhook(
        self,
        entity_type: str,
        action: str,
        url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Найти вебхук по параметрам (строгое соответствие).
        
        Args:
            entity_type: Тип сущности
            action: Действие
            url: URL вебхука
            
        Returns:
            Данные вебхука или None
        """
        webhooks = await self.list_webhooks()
        
        logger.debug(
            "Поиск вебхука (strict): entity_type=%s, action=%s, url=%s",
            entity_type, action, url
        )
        
        for webhook in webhooks:
            if (
                webhook.get("entityType") == entity_type
                and webhook.get("action") == action
                and webhook.get("url") == url
            ):
                logger.info("Найден вебхук (strict match): id=%s", webhook.get("id"))
                return webhook
        
        logger.warning("Вебхук не найден (strict match)")
        return None
    
    async def find_webhook_relaxed(
        self,
        entity_type: str,
        action: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Найти вебхук по entity_type и action (игнорируя URL и enabled).
        
        Args:
            entity_type: Тип сущности
            action: Действие
            
        Returns:
            Данные вебхука или None
        """
        webhooks = await self.list_webhooks()
        
        logger.debug(
            "Поиск вебхука (relaxed): entity_type=%s, action=%s",
            entity_type, action
        )
        
        for webhook in webhooks:
            if (
                webhook.get("entityType") == entity_type
                and webhook.get("action") == action
            ):
                logger.info(
                    "Найден вебхук (relaxed match): id=%s, url=%s, enabled=%s",
                    webhook.get("id"),
                    webhook.get("url"),
                    webhook.get("enabled"),
                )
                return webhook
        
        logger.warning("Вебхук не найден (relaxed match)")
        return None
    
    async def delete_webhook(self, webhook_id: str) -> bool:
        """
        Удалить вебхук из МойСклад.
        
        Args:
            webhook_id: ID вебхука
            
        Returns:
            True если успешно удален, False если не найден
            
        Raises:
            MoySkladAPIError: При ошибке запроса
        """
        try:
            base_url = self._get_base_url()
            headers = self._get_headers()
            
            async with httpx.AsyncClient(headers=headers, timeout=self._timeout) as client:
                url = f"{base_url}/entity/webhook/{webhook_id}"
                logger.info("Удаление вебхука из МойСклад: %s", webhook_id)
                
                resp = await client.delete(url)
                resp.raise_for_status()
                
                logger.info("Вебхук успешно удален из МойСклад: %s", webhook_id)
                return True
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.warning("Вебхук не найден в МойСклад: %s", webhook_id)
                return False
            raise MoySkladAPIError(
                "Ошибка HTTP при удалении вебхука",
                details={"status_code": exc.response.status_code, "error": str(exc)},
            ) from exc
        except Exception as exc:
            raise MoySkladAPIError(
                "Ошибка при удалении вебхука",
                details={"error": str(exc)},
            ) from exc