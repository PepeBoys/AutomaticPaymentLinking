# Базовый модуль payment_base - Платежные документы

## Описание

Модуль `payment_base` предоставляет базовую функциональность для всех платежных документов МойСклад, которые осуществляют оплату других документов. Это фундаментальный модуль, от которого наследуются paymentin, cashin (входящие платежи), paymentout, cashout (исходящие платежи).

**Важно**: Это **базовый модуль** без собственных REST API endpoints. Он предоставляет только базовые классы, методы и утилиты для наследования.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           БАЗОВЫЙ МОДУЛЬ                                    │
│                    (БЕЗ REST API, ТОЛЬКО БАЗОВЫЕ КЛАССЫ)                    │
└─────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                        DOMAIN LAYER (BASE)                                 ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────┐        ║
║  │                BasePaymentEntity                               │        ║
║  ├────────────────────────────────────────────────────────────────┤        ║
║  │  Базовая сущность для всех платежных документов                │        ║
║  │  • id, account_id, name, moment, applicable                    │        ║
║  │  • sum, agent_id, organization_id                              │        ║
║  │  • payment_purpose (назначение платежа)                        │        ║
║  │  • linked_operations (связанные документы)                     │        ║
║  │  • meta_href, project_meta_href, sales_channel_meta_href       │        ║
║  └────────────────────────────────────────────────────────────────┘        ║
║                              △                                            ║
║                              │ наследуют                                   ║
║                              │                                            ║
║  ┌───────────────────────────┴────────────────────────────────────┐       ║
║  │                                                                │       ║
║  │  PaymentInEntity    CashInEntity                               │       ║
║  │  PaymentOutEntity   CashOutEntity                              │       ║
║  │                                                                │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
║  ┌────────────────────────────────────────────────────────────────┐       ║
║  │              BasePaymentFilter (Value Object)                  │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  • agent_id: str | None                                        │       ║
║  │  • organization_id: str | None                                 │       ║
║  │  • project_href: str | None                                    │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                        SERVICE LAYER (BASE)                                ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────┐        ║
║  │  BasePaymentService<TEntity, TClient>  (Generic)               │        ║
║  ├────────────────────────────────────────────────────────────────┤        ║
║  │  Бизнес-логика работы с платежами                              │        ║
║  │                                                                │        ║
║  │  • get_by_id(payment_id)                                       │        ║
║  │    Получить платеж по ID                                       │        ║
║  │                                                                │        ║
║  │  • get_by_href(href)                                           │        ║
║  │    Получить платеж по прямой ссылке                            │        ║
║  │                                                                │        ║
║  │  • link_to_document(payment_id, document_href, linked_sum)     │        ║
║  │    Привязать платеж к документу                                │        ║
║  │                                                                │        ║
║  │  • update_state(payment_id, state_id)                          │        ║
║  │    Обновить статус платежа                                     │        ║
║  │                                                                │        ║
║  │  • update_project(payment_id, project_href)                    │        ║
║  │    Обновить проект платежа                                     │        ║
║  │                                                                │        ║
║  │  • update_sales_channel(payment_id, sales_channel_href)        │        ║
║  │    Обновить канал продаж                                       │        ║
║  │                                                                │        ║
║  │  • get_states()                                                │        ║
║  │    Получить список статусов                                    │        ║
║  └────────────────────────────────────────────────────────────────┘        ║
║                              △                                            ║
║                              │ наследуют                                   ║
║                              │                                             ║
║  ┌───────────────────────────┴────────────────────────────────────┐        ║
║  │                                                                │        ║
║  │  PaymentInService     CashInService                            │        ║
║  │  PaymentOutService    CashOutService                           │        ║
║  │                                                                │        ║
║  └────────────────────────────────────────────────────────────────┘        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                        CLIENT LAYER (BASE)                                 ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ┌────────────────────────────────────────────────────────────────┐        ║
║  │              BasePaymentClient (ABC)                           │        ║
║  ├────────────────────────────────────────────────────────────────┤        ║
║  │  Работа с МойСклад API для платежей                            │        ║
║  │                                                                │        ║
║  │  • get_by_href(href)                                           │        ║
║  │    Получить платеж по прямой ссылке                            │        ║
║  │                                                                │        ║
║  │  • update_operations(payment_id, operations)                   │        ║
║  │    Обновить связанные документы платежа                        │        ║
║  │                                                                │        ║
║  │  • update_state(payment_id, state_id)                          │        ║
║  │    Обновить статус платежа                                     │        ║
║  │                                                                │        ║
║  │  • update_project(payment_id, project_href)                    │        ║
║  │    Обновить проект платежа                                     │        ║
║  │                                                                │        ║
║  │  • update_sales_channel(payment_id, sales_channel_href)        │        ║
║  │    Обновить канал продаж платежа                               │        ║
║  │                                                                │        ║
║  │  • get_states()                                                │        ║
║  │    Получить метаданные статусов                                │        ║
║  └────────────────────────────────────────────────────────────────┘        ║
║                              △                                            ║
║                              │ наследуют                                   ║
║                              │                                             ║
║  ┌───────────────────────────┴────────────────────────────────────┐        ║
║  │                                                                │        ║
║  │  PaymentInClient     CashInClient                              │        ║
║  │  PaymentOutClient    CashOutClient                             │        ║
║  │                                                                │        ║
║  └────────────────────────────────────────────────────────────────┘        ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                    EXCEPTION HANDLING                                      ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  BasePaymentException   →  500 INTERNAL_SERVER_ERROR                       ║
║  PaymentNotFoundError   →  404 NOT_FOUND                                   ║
║  PaymentAPIError        →  502 BAD_GATEWAY                                 ║
║                                                                            ║
║  Exception handlers:                                                       ║
║  • base_payment_exception_handler                                          ║
║  • payment_not_found_handler                                               ║
║  • payment_api_error_handler                                               ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Основные компоненты

### 1. Доменная модель
```
┌────────────────────────────────────────────────────────────────┐
│                BasePaymentEntity                               │
├────────────────────────────────────────────────────────────────┤
│  Обязательные поля:                                            │
│  • id: str                    - UUID платежа                   │
│  • account_id: str            - ID учетной записи              │
│  • name: str                  - Номер платежа                  │
│  • moment: datetime           - Дата платежа                   │
│  • applicable: bool           - Проведен ли платеж             │
│  • sum: float                 - Сумма платежа                  │
│  • agent_id: str              - Контрагент (от кого/кому)      │
│  • organization_id: str       - Организация (наша компания)    │
│  • payment_purpose: str | None - Назначение платежа            │
│  • linked_operations: list[dict] - Связанные документы         │
│  • meta_href: str             - Ссылка на платеж в API         │
│                                                                │
│  Опциональные поля:                                            │
│  • project_meta_href: str | None      - Ссылка на проект       │
│  • sales_channel_meta_href: str | None - Канал продаж          │
│                                                                │
│  ВАЖНО: Нет domain методов                                     │
│  (в отличие от BasePayableDocumentEntity)                      │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│              BasePaymentFilter                                 │
│              (Value Object)                                    │
├────────────────────────────────────────────────────────────────┤
│  • agent_id: str | None                                        │
│    Фильтр по контрагенту                                       │
│                                                                │
│  • organization_id: str | None                                 │
│    Фильтр по организации                                       │
│                                                                │
│  • project_href: str | None                                    │
│    Фильтр по проекту                                           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2. Сервисный слой
```
┌────────────────────────────────────────────────────────────────┐
│       BasePaymentService<TEntity, TClient>                     │
│                  (Generic Abstract Base)                       │
├────────────────────────────────────────────────────────────────┤
│  Абстрактные методы (требуют реализации):                      │
│                                                                │
│  entity_type() -> str                                          │
│    Тип сущности ("paymentin", "cashout", ...)                  │
│                                                                │
│  _to_entity(data: dict) -> TEntity                             │
│    Преобразование JSON из API в доменную сущность              │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Унаследованные методы (готовые к использованию):              │
│                                                                │
│  get_by_id(payment_id: str) -> TEntity                         │
│                                                                │
│    Получить платеж по ID                                       │
│    Строит href из base_url + entity_type + payment_id          │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_by_href(href: str) -> TEntity                             │
│                                                                │
│    Получить платеж по прямой ссылке                            │
│    Используется в webhook для получения платежа из payload     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  link_to_document(                                             │
│    payment_id: str,                                            │
│    document_meta_href: str,                                    │
│    linked_sum: float                                           │
│  ) -> TEntity                                                  │
│                                                                │
│    Привязать платеж к документу                                │
│                                                                │
│    Логика:                                                     │
│    1. Получить текущий платеж                                  │
│    2. Сохранить существующие operations                        │
│    3. Добавить новый документ                                  │
│    4. Обновить operations через API                            │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_state(payment_id: str, state_id: str) -> TEntity       │
│                                                                │
│    Обновить статус платежа                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_project(payment_id: str, project_href: str) -> TEntity │
│                                                                │
│    Обновить проект платежа                                     │
│    Используется для автоматической установки проекта           │
│    из связанного документа                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_sales_channel(                                         │
│    payment_id: str,                                            │
│    sales_channel_href: str                                     │
│  ) -> TEntity                                                  │
│                                                                │
│    Обновить канал продаж платежа                               │
│    Используется для автоматической установки канала            │
│    из связанного документа                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_states() -> list[dict]                                    │
│                                                                │
│    Получить список доступных статусов                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3. Клиентский слой
```
┌────────────────────────────────────────────────────────────────┐
│              BasePaymentClient (ABC)                           │
├────────────────────────────────────────────────────────────────┤
│  Абстрактные методы:                                           │
│                                                                │
│  entity_type() -> str                                          │
│    Тип сущности для URL API                                    │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Унаследованные методы:                                        │
│                                                                │
│  get_by_href(href: str) -> dict                                │
│                                                                │
│    GET {href}                                                  │
│    Получить платеж по прямой ссылке                            │
│                                                                │
│    Retry: 3 попытки с exponential backoff (2-10 сек)           │
│    Throws: PaymentNotFoundError (404)                          │
│            PaymentAPIError (другие ошибки)                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_operations(                                            │
│    payment_id: str,                                            │
│    operations: list[dict]                                      │
│  ) -> dict                                                     │
│                                                                │
│    PUT /entity/{type}/{payment_id}                             │
│    {operations: [...]}                                         │
│                                                                │
│    Обновить массив связанных документов                        │
│                                                                │
│    Retry: 3 попытки                                            │
│    Throws: PaymentNotFoundError (404)                          │
│            PaymentAPIError (другие ошибки)                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_state(payment_id: str, state_id: str) -> dict          │
│                                                                │
│    PUT /entity/{type}/{payment_id}                             │
│    {state: {meta: {...}}}                                      │
│                                                                │
│    Обновить статус платежа                                     │
│                                                                │
│    NO Retry (дизайн-решение)                                   │
│    Throws: PaymentAPIError                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_project(payment_id: str, project_href: str) -> dict    │
│                                                                │
│    PUT /entity/{type}/{payment_id}                             │
│    {project: {meta: {...}}}                                    │
│                                                                │
│    Обновить проект                                             │
│                                                                │
│    NO Retry (дизайн-решение)                                   │
│    Throws: PaymentAPIError                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_sales_channel(                                         │
│    payment_id: str,                                            │
│    sales_channel_href: str                                     │
│  ) -> dict                                                     │
│                                                                │
│    PUT /entity/{type}/{payment_id}                             │
│    {salesChannel: {meta: {...}}}                               │
│                                                                │
│    Обновить канал продаж                                       │
│                                                                │
│    NO Retry (дизайн-решение)                                   │
│    Throws: PaymentAPIError                                     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_states() -> list[dict]                                    │
│                                                                │
│    GET /entity/{type}/metadata                                 │
│    Получить метаданные статусов                                │
│                                                                │
│    NO Retry (дизайн-решение)                                   │
│    Throws: PaymentAPIError                                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Процесс работы

### Получение платежа из webhook
```
WebhookHandler   PaymentService   BasePaymentClient   МойСклад API
     │                  │                   │                   │
     │  get_by_href()   │                   │                   │
     │  (from webhook   │                   │                   │
     │   payload)       │                   │                   │
     ├─────────────────►│                   │                   │
     │                  │  get_by_href()    │                   │
     │                  ├──────────────────►│                   │
     │                  │                   │  GET {href}       │
     │                  │                   ├──────────────────►│
     │                  │                   │  payment_data     │
     │                  │                   │◄──────────────────┤
     │                  │  _to_entity()     │                   │
     │                  │  TEntity          │                   │
     │                  │◄──────────────────┤                   │
     │  payment         │                   │                   │
     │◄─────────────────┤                   │                   │
     │                  │                   │                   │
```

### Привязка платежа к документу
```
WebhookHandler   PaymentService   BasePaymentClient   МойСклад API
     │                  │                   │                   │
     │  link_to_        │                   │                   │
     │  document()      │                   │                   │
     ├─────────────────►│                   │                   │
     │                  │                   │                   │
     │                  │  ┌──────────────────────────────┐     │
     │                  │  │ 1. Получить текущий платеж   │     │
     │                  │  └──────────────────────────────┘     │
     │                  │  get_by_href()    │                   │
     │                  ├──────────────────►│  GET {href}       │
     │                  │                   ├──────────────────►│
     │                  │                   │  payment_data     │
     │                  │                   │◄──────────────────┤
     │                  │                   │                   │
     │                  │  ┌──────────────────────────────────┐ │
     │                  │  │ 2. Построить новый operations:   │ │
     │                  │  │    • Сохранить старые            │ │
     │                  │  │    • Добавить новый документ     │ │
     │                  │  └──────────────────────────────────┘ │
     │                  │                   │                   │
     │                  │  update_operations()                  │
     │                  ├──────────────────►│                   │
     │                  │                   │  PUT /payment/{id}│
     │                  │                   │  {operations:[...]}
     │                  │                   ├──────────────────►│
     │                  │                   │  updated_payment  │
     │                  │                   │◄──────────────────┤
     │                  │  _to_entity()     │                   │
     │                  │  TEntity          │                   │
     │                  │◄──────────────────┤                   │
     │  payment         │                   │                   │
     │◄─────────────────┤                   │                   │
     │                  │                   │                   │
```

## Отличия от payable_document_base
```
╔═══════════════════════════════════════════════════════════════════╗
║        PAYMENT_BASE vs PAYABLE_DOCUMENT_BASE                      ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ┌──────────────────┬──────────────────┬────────────────────┐     ║
║  │ Аспект           │ payment_base     │ payable_document   │     ║
║  ├──────────────────┼──────────────────┼────────────────────┤     ║
║  │ Роль             │ ДЕЛАЕТ оплату    │ ПОЛУЧАЕТ оплату    │     ║
║  │                  │ (платеж)         │ (документ)         │     ║
║  │                  │                  │                    │     ║
║  │ Ключевые поля    │ payment_purpose  │ payed_sum          │     ║
║  │                  │ linked_operations│ shipped_sum        │     ║
║  │                  │                  │ invoiced_sum       │     ║
║  │                  │                  │                    │     ║
║  │ Domain методы    │ НЕТ              │ is_fully_paid()    │     ║
║  │                  │                  │ get_unpaid()       │     ║
║  │                  │                  │ matches_sum()      │     ║
║  │                  │                  │                    │     ║
║  │ Основные методы  │ get_by_href()    │ search()           │     ║
║  │                  │ link_to_document │ find_for_payment() │     ║
║  │                  │ update_operations│ search_by_agent    │     ║
║  │                  │                  │                    │     ║
║  │ Типы             │ paymentin,       │ customerorder,     │     ║
║  │                  │ paymentout,      │ invoiceout,        │     ║
║  │                  │ cashin, cashout  │ demand, ...        │     ║
║  │                  │                  │                    │     ║
║  │ Использование    │ Привязка к       │ Поиск для          │     ║
║  │                  │ документам       │ привязки платежа   │     ║
║  └──────────────────┴──────────────────┴────────────────────┘     ║
║                                                                   ║
║  ВАЖНО: Это дополняющие друг друга модули!                        ║
║  • Платежи (payment_base) привязываются К документам              ║
║  • Документы (payable_document_base) ищутся ДЛЯ платежей          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Особенности реализации
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. GENERIC ТИПЫ                                                  ║
║     BasePaymentService<TEntity, TClient>                          ║
║     • TEntity: bound=BasePaymentEntity                            ║
║     • TClient: bound=BasePaymentClient                            ║
║     • Строгая типизация наследников                               ║
║                                                                   ║
║  2. RETRY МЕХАНИЗМ (ЧАСТИЧНЫЙ)                                    ║
║     С retry:                                                      ║
║     • get_by_href() - 3 попытки, exponential backoff              ║
║     • update_operations() - 3 попытки                             ║
║                                                                   ║
║     БЕЗ retry:                                                    ║
║     • update_state() - дизайн-решение                             ║
║     • update_project() - дизайн-решение                           ║
║     • update_sales_channel() - дизайн-решение                     ║
║     • get_states() - дизайн-решение                               ║
║                                                                   ║
║  3. LINKED_OPERATIONS                                             ║
║     Массив связанных документов:                                  ║
║     [                                                             ║
║       {                                                           ║
║         "meta": {"href": "...", "type": "customerorder"},         ║
║         "linkedSum": 10000.0                                      ║
║       }                                                           ║
║     ]                                                             ║
║                                                                   ║
║     При добавлении нового документа:                              ║
║     • Сохраняются все существующие operations                     ║
║     • Добавляется новый с linkedSum                               ║
║                                                                   ║
║  4. PAYMENT_PURPOSE ПАРСИНГ                                       ║
║     Назначение платежа может содержать:                           ║
║     • Номер документа ("Оплата по счету INV-00042")               ║
║     • Дата документа                                              ║
║     • Другую полезную информацию                                  ║
║                                                                   ║
║     Используется в WebhookHandler для поиска документов           ║
║                                                                   ║
║  5. TYPE EXTRACTION                                               ║
║     _extract_type_from_href(href) -> str                          ║
║     Извлекает тип документа из href:                              ║
║     ".../entity/customerorder/123" → "customerorder"              ║
║                                                                   ║
║  6. НЕТ DOMAIN МЕТОДОВ                                            ║
║     В отличие от payable_document_base,                           ║
║     BasePaymentEntity не имеет методов                            ║
║     (is_fully_paid, get_unpaid_amount, etc.)                      ║
║                                                                   ║
║     Причина: Платежи не имеют "неоплаченной суммы"                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Создание наследника Entity
```python
from dataclasses import dataclass
from apps.payment_base.domain.entities import BasePaymentEntity

@dataclass
class PaymentInEntity(BasePaymentEntity):
    """Входящий платеж - наследует все поля."""
    pass  # Можно добавить дополнительные поля если нужно
```

### Создание наследника Service
```python
from apps.payment_base.services.base_service import BasePaymentService
from apps.payment_base.services.base_client import BasePaymentClient

class PaymentInService(BasePaymentService[PaymentInEntity, PaymentInClient]):
    """Сервис для входящих платежей."""
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, PaymentInClient(auth_service))
    
    @property
    def entity_type(self) -> str:
        """Тип сущности в МойСклад API."""
        return "paymentin"
    
    @staticmethod
    def _to_entity(data: dict) -> PaymentInEntity:
        """Преобразовать JSON в entity."""
        # Парсинг полей из data
        return PaymentInEntity(
            id=data["id"],
            account_id=data["accountId"],
            # ... остальные поля
        )

# Использование унаследованных методов
service = PaymentInService(auth_service)

# Получить платеж из webhook
payment = await service.get_by_href(href_from_webhook)

# Привязать к документу
payment = await service.link_to_document(
    payment_id="payment_123",
    document_meta_href="entity/customerorder/order_456",
    linked_sum=10000.0
)

# Обновить статус
await service.update_state(
    payment_id="payment_123",
    state_id="state_paid"
)
```

### Создание наследника Client
```python
from apps.payment_base.services.base_client import BasePaymentClient

class PaymentInClient(BasePaymentClient):
    """Клиент для входящих платежей."""
    
    @property
    def entity_type(self) -> str:
        """Тип сущности для URL."""
        return "paymentin"

# Использование унаследованных методов
client = PaymentInClient(auth_service)

# Получить по href
payment = await client.get_by_href(href)

# Обновить operations
updated = await client.update_operations(
    payment_id="payment_123",
    operations=[
        {
            "meta": {
                "href": ".../customerorder/order_456",
                "type": "customerorder",
                "mediaType": "application/json"
            },
            "linkedSum": 10000.0
        }
    ]
)
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│              ИСПОЛЬЗУЕТСЯ В (НАСЛЕДНИКИ)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ВХОДЯЩИЕ ПЛАТЕЖИ (от покупателей):                             │
│  • paymentin  - Входящий платеж (безналичный)                   │
│  • cashin     - Приходный кассовый ордер (наличный)             │
│                                                                 │
│  ИСХОДЯЩИЕ ПЛАТЕЖИ (поставщикам):                               │
│  • paymentout - Исходящий платеж (безналичный)                  │
│  • cashout    - Расходный кассовый ордер (наличный)             │
│                                                                 │
│  Все эти модули наследуют:                                      │
│  • BasePaymentEntity                                            │
│  • BasePaymentService<TEntity, TClient>                         │
│  • BasePaymentClient                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИТ ОТ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ms_auth.MySkladAuthService                                     │
│    └─► Аутентификация для API запросов                          │
│                                                                 │
│  core.config.settings                                           │
│    └─► WEBHOOK_RETRY_ATTEMPTS, WEBHOOK_TIMEOUT                  │
│                                                                 │
│  External libraries:                                            │
│  • httpx - HTTP клиент                                          │
│  • tenacity - Retry механизм                                    │
│  • pydantic - Валидация схем                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  РАБОТАЕТ СОВМЕСТНО С                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  payable_document_base                                          │
│    └─► Платежи привязываются к документам                       │
│        payment.link_to_document(document.meta_href)             │
│                                                                 │
│  hooks.WebhookHandler                                           │
│    └─► Использует PaymentService для обработки webhook          │
│        1. Получить платеж через get_by_href()                   │
│        2. Найти документы через DocumentService                 │
│        3. Привязать через link_to_document()                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Тестирование
```
┌─────────────────────────────────────────────────────────────────┐
│              РЕКОМЕНДУЕМЫЕ СЦЕНАРИИ ТЕСТИРОВАНИЯ                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLIENT LAYER                                                   │
│  ✓ 1. get_by_href() - успешное получение                        │
│  ✓ 2. get_by_href() - 404 (PaymentNotFoundError)                │
│  ✓ 3. get_by_href() - retry на сетевой ошибке                   │
│  ✓ 4. update_operations() - успешное обновление                 │
│  ✓ 5. update_operations() - 404 (PaymentNotFoundError)          │
│  ✓ 6. update_operations() - retry механизм                      │
│  ✓ 7. update_state() - успешное обновление                      │
│  ✓ 8. update_project() - успешное обновление                    │
│  ✓ 9. update_sales_channel() - успешное обновление              │
│  ✓ 10. get_states() - получение статусов                        │
│                                                                 │
│  SERVICE LAYER                                                  │
│  ✓ 11. get_by_id() - построение href и получение                │
│  ✓ 12. get_by_href() - прямое получение                         │
│  ✓ 13. link_to_document() - добавление нового документа         │
│  ✓ 14. link_to_document() - сохранение старых operations        │
│  ✓ 15. link_to_document() - _extract_type_from_href()           │
│  ✓ 16. update_state() - делегация в client                      │
│  ✓ 17. update_project() - делегация в client                    │
│  ✓ 18. update_sales_channel() - делегация в client              │
│                                                                 │
│  EXCEPTION HANDLING                                             │
│  ✓ 19. PaymentNotFoundError - 404                               │
│  ✓ 20. PaymentAPIError - 502                                    │
│  ✓ 21. BasePaymentException - 500                               │
│                                                                 │
│  INTEGRATION                                                    │
│  ✓ 22. Полный цикл: webhook → get → link → update              │
│  ✓ 23. Множественные документы в operations                     │
│  ✓ 24. Изоляция по account_id                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Архитектурное решение: базовый модуль
```
╔═══════════════════════════════════════════════════════════════════╗
║            ПОЧЕМУ БАЗОВЫЙ МОДУЛЬ С НАСЛЕДОВАНИЕМ?                 ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ПРОБЛЕМА БЕЗ БАЗОВОГО МОДУЛЯ:                                    ║
║                                                                   ║
║  • 4 типа платежей (paymentin, paymentout, cashin, cashout)       ║
║  • Каждый реализует похожую логику                                ║
║  • Дублирование кода: get_by_href(), link_to_document(), ...      ║
║  • Несогласованность в разных модулях                             ║
║  • Сложность поддержки: изменения в 4 местах                      ║
║                                                                   ║
║  РЕШЕНИЕ: БАЗОВЫЙ МОДУЛЬ                                          ║
║                                                                   ║
║  Преимущества:                                                    ║
║  1. DRY - код написан один раз                                    ║
║  2. Consistency - все платежи работают одинаково                  ║
║  3. Maintainability - изменения в одном месте                     ║
║  4. Testability - тесты базового модуля покрывают всех            ║
║  5. Extensibility - легко добавить новый тип платежа              ║
║                                                                   ║
║  Недостатки (trade-offs):                                         ║
║  1. Сложность понимания для новых разработчиков                   ║
║  2. Generic типы могут быть непривычны                            ║
║  3. Иерархия наследования требует дисциплины                      ║
║                                                                   ║
║  ВЕРДИКТ: Правильное решение для 4 похожих модулей                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```