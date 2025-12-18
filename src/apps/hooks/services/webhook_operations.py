"""Операции с вебхуками (Strategy Pattern)."""

import logging
from abc import ABC, abstractmethod
from typing import Dict

from ..domain.entities import WebhookEntity, WebhookOperationResult
from ..domain.value_objects import WebhookConfiguration
from .moysklad_client import MoySkladClient

logger = logging.getLogger(__name__)


class WebhookOperation(ABC):
    """Абстрактная операция с вебхуком (Strategy Pattern)."""
    
    def __init__(
        self,
        client: MoySkladClient,
        config: WebhookConfiguration,
        existing_db_entity: WebhookEntity | None = None,
    ) -> None:
        """
        Инициализировать операцию.
        
        Args:
            client: Клиент МойСклад API
            config: Конфигурация вебхука
        """
        self._client = client
        self._config = config
        self._existing_db_entity = existing_db_entity

    async def _get_webhook_from_db_reference(self) -> Dict | None:
        """Попробовать получить вебхук по ссылке из БД (по ms_webhook_id).

        Возвращает None, если записи нет или вебхук не найден в МойСклад.
        """

        if not self._existing_db_entity:
            return None

        webhook_id = self._existing_db_entity.ms_webhook_id
        if not webhook_id:
            return None

        logger.info(
            "Пробуем найти вебхук по сохраненному ID из БД: %s", webhook_id
        )

        try:
            webhook = await self._client.get_webhook_by_id(webhook_id)
        except Exception as exc:
            logger.warning(
                "Не удалось получить вебхук по сохраненному ID %s: %s. Продолжаем поиск.",
                webhook_id,
                str(exc),
            )
            return None

        if not webhook:
            return None

        if webhook.get("entityType") != self._config.entity_type or webhook.get(
            "action"
        ) != self._config.action:
            logger.warning(
                "Найден вебхук по ID, но тип/действие отличаются: db(entity=%s, action=%s), api(entity=%s, action=%s)",
                self._existing_db_entity.entity_type,
                self._existing_db_entity.action,
                webhook.get("entityType"),
                webhook.get("action"),
            )

        if webhook.get("url") != self._config.url:
            logger.info(
                "URL вебхука по сохраненному ID отличается от ожидаемого. Ожидали: %s, получили: %s",
                self._config.url,
                webhook.get("url"),
            )

        return webhook
    
    def _webhook_data_to_entity(self, webhook_data: Dict, *, enabled_fallback: bool | None = None) -> WebhookEntity:
        """Преобразовать данные API в доменную сущность с учетом текущей конфигурации."""

        meta = webhook_data.get("meta") or {}
        enabled_value = webhook_data.get("enabled", enabled_fallback)

        return WebhookEntity(
            payment_type=self._config.payment_type,
            entity_type=webhook_data.get("entityType", ""),
            action=webhook_data.get("action", ""),
            url=webhook_data.get("url", ""),
            ms_webhook_id=webhook_data.get("id", ""),
            ms_href=meta.get("href"),
            ms_account_id=webhook_data.get("accountId"),
            enabled=bool(enabled_value) if enabled_value is not None else False,
        )
    
    @abstractmethod
    async def execute(self) -> WebhookOperationResult:
        """
        Выполнить операцию.
        
        Returns:
            Результат операции
        """
        raise NotImplementedError


class EnableWebhookOperation(WebhookOperation):
    """Операция включения вебхука."""
    
    async def execute(self) -> WebhookOperationResult:
        logger.info("Выполнение EnableWebhookOperation: entity_type=%s, action=%s, url=%s",
                    self._config.entity_type, self._config.action, self._config.url)
        
        existing = await self._get_webhook_from_db_reference()

        if not existing:
            existing = await self._client.find_webhook(
                entity_type=self._config.entity_type,
                action=self._config.action,
                url=self._config.url,
            )
        
        if not existing:
            logger.info("Существующий вебхук не найден, создаем новый")
            return await self._create_new_webhook()
        
        logger.info(
            "Найден существующий вебхук: id=%s, enabled=%s",
            existing.get("id"),
            existing.get("enabled"),
        )

        url_matches = existing.get("url") == self._config.url
        enabled = existing.get("enabled") is True

        if url_matches and enabled:
            return self._already_enabled_result(existing)
        
        if not url_matches:
            return await self._update_url_and_enable(existing)
        
        logger.info("Вебхук найден но выключен, включаем")
        
        return await self._enable_existing_webhook(existing)
    
    async def _create_new_webhook(self) -> WebhookOperationResult:
        """Создать новый вебхук."""
        webhook_data = await self._client.create_webhook(
            entity_type=self._config.entity_type,
            action=self._config.action,
            url=self._config.url,
        )
        
        entity = self._webhook_data_to_entity(webhook_data, enabled_fallback=True)
        logger.info("Создан новый вебхук: %s", entity.ms_webhook_id)
        
        return WebhookOperationResult(
            operation="created_and_enabled",
            success=True,
            webhook_entity=entity,
        )
    
    async def _enable_existing_webhook(self, existing: Dict) -> WebhookOperationResult:
        """Активировать существующий вебхук."""
        updated = await self._client.update_webhook(
            webhook_data=existing,
            enabled=True,
        )
        
        entity = self._webhook_data_to_entity(updated, enabled_fallback=True)
        logger.info("Вебхук включен: %s", entity.ms_webhook_id)
        
        return WebhookOperationResult(
            operation="enabled",
            success=True,
            webhook_entity=entity,
        )
    
    async def _update_url_and_enable(self, existing: Dict) -> WebhookOperationResult:
        """Обновить url вебхука и включить его."""
        updated = await self._client.update_webhook(
            webhook_data=existing,
            enabled=True,
            url=self._config.url,
        )

        entity = self._webhook_data_to_entity(updated, enabled_fallback=True)
        logger.info(
            "Вебхук url обновлен и включен: %s (url=%s)",
            entity.ms_webhook_id,
            entity.url,
        )

        return WebhookOperationResult(
            operation="url_updated_and_enabled",
            success=True,
            webhook_entity=entity,
        )

    
    def _already_enabled_result(self, existing: Dict) -> WebhookOperationResult:
        """Вебхук уже включен."""
        entity = self._webhook_data_to_entity(existing, enabled_fallback=True)
        
        return WebhookOperationResult(
            operation="already_enabled",
            success=True,
            webhook_entity=entity,
        )


class DisableWebhookOperation(WebhookOperation):
    """Операция отключения вебхука."""
    
    async def execute(self) -> WebhookOperationResult:
        existing = await self._get_webhook_from_db_reference()

        if not existing:
            existing = await self._client.find_webhook(
                entity_type=self._config.entity_type,
                action=self._config.action,
                url=self._config.url,
            )
        
        if not existing:
            return self._not_found_result()
        
        if existing.get("enabled") is False:
            return self._already_disabled_result(existing)
        
        return await self._disable_existing_webhook(existing)
    
    async def _disable_existing_webhook(self, existing: Dict) -> WebhookOperationResult:
        """Деактивировать существующий вебхук."""
        updated = await self._client.update_webhook(
            webhook_data=existing,
            enabled=False,
        )

        entity = self._webhook_data_to_entity(updated, enabled_fallback=False)

        logger.info("Вебхук выключен: %s", entity.ms_webhook_id)
        
        return WebhookOperationResult(
            operation="disabled",
            success=True,
            webhook_entity=entity,
        )
    
    def _not_found_result(self) -> WebhookOperationResult:
        """Вебхук не найден."""
        return WebhookOperationResult(
            operation="not_found_to_disable",
            success=True,
            message="Вебхук не найден",
        )
    
    def _already_disabled_result(self, existing: Dict) -> WebhookOperationResult:
        """Вебхук уже отключен."""
        
        entity = self._webhook_data_to_entity(existing, enabled_fallback=False)

        return WebhookOperationResult(
            operation="already_disabled",
            success=True,
            webhook_entity=entity,
        )


class WebhookOperationFactory:
    """Фабрика для создания операций с вебхуками (Factory Pattern)."""
    
    @staticmethod
    def create_operation(
        enabled: bool,
        client: MoySkladClient,
        config: WebhookConfiguration,
        existing_db_entity: WebhookEntity | None = None,
    ) -> WebhookOperation:
        """
        Создать операцию в зависимости от требуемого действия.
        
        Args:
            enabled: True для включения, False для отключения
            client: Клиент МойСклад API
            config: Конфигурация вебхука
            
        Returns:
            Операция с вебхуком
        """
        if enabled:
            return EnableWebhookOperation(client, config, existing_db_entity)
        else:
            return DisableWebhookOperation(client, config, existing_db_entity)