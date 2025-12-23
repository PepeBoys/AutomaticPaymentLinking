# Приложение paymentin - Входящие платежи

## Описание

Модуль `paymentin` реализует работу с входящими безналичными платежами от покупателей в системе МойСклад. Это **наследник** модуля `payment_base`, добавляющий минимальный специфичный функционал и REST API endpoint.

**Ключевое назначение**: Обработка webhook'ов о входящих платежах и автоматическая привязка к документам (заказам покупателей, счетам, отгрузкам).

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (REST)                                    │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  api.py - REST Endpoints                                           │     │
│  │  • GET  /{payment_id}  → Получить входящий платеж по ID            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY INJECTION                                │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  dependencies.py                                                 │       │
│  │  • get_paymentin_service() → PaymentInService                    │       │
│  │  • PaymentInSvcDep = Annotated[...]                              │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                                        │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  PaymentInService                                                │       │
│  │  extends BasePaymentService<PaymentInEntity, PaymentInClient>    │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  Собственный код (~30 строк):                                    │       │
│  │  • entity_type = "paymentin"                                     │       │
│  │  • _to_entity(data) - парсинг JSON → PaymentInEntity             │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  Унаследованные методы (~500 строк):                             │       │
│  │  • get_by_id(payment_id)                                         │       │
│  │  • get_by_href(href)                                             │       │
│  │  • link_to_document(payment_id, document_href, sum)              │       │
│  │  • update_state(payment_id, state_id)                            │       │
│  │  • update_project(payment_id, project_href)                      │       │
│  │  • update_sales_channel(payment_id, sales_channel_href)          │       │
│  │  • get_states()                                                  │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                         │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  PaymentInClient                                                 │       │
│  │  extends BasePaymentClient                                       │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  Собственный код (~8 строк):                                     │       │
│  │  • entity_type = "paymentin"                                     │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  Унаследованные методы (~250 строк):                             │       │
│  │  • get_by_href(href)                                             │       │
│  │  • update_operations(payment_id, operations)                     │       │
│  │  • update_state(payment_id, state_id)                            │       │
│  │  • update_project(payment_id, project_href)                      │       │
│  │  • update_sales_channel(payment_id, sales_channel_href)          │       │
│  │  • get_states()                                                  │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                                         │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  PaymentInEntity                                                 │       │
│  │  extends BasePaymentEntity                                       │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  Собственный код: 0 строк (pass)                                 │       │
│  │  Унаследованные поля: ~15 полей                                  │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  PaymentInFilter (Value Object)                                  │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │  • agent_id, sum_value, sum_tolerance                            │       │
│  │  • date_from, date_to                                            │       │
│  │  • to_moysklad_filter() -> str                                   │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                    EXCEPTIONS & SCHEMAS (ALIASES)                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Исключения - просто алиасы от payment_base:                               ║
║  • PaymentInBaseException = BasePaymentException                           ║
║  • PaymentInAPIError = PaymentAPIError                                     ║
║  • PaymentInNotFoundError = PaymentNotFoundError                           ║
║                                                                            ║
║  Схемы - просто наследование от payment_base:                              ║
║  • PaymentInResponse(BasePaymentResponse): pass                            ║
║  • Используются: MetaRef, Agent, Organization, LinkedOperation             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Основные компоненты

### 1. REST API
```
┌────────────────────────────────────────────────────────────────┐
│                    GET /{payment_id}                           │
├────────────────────────────────────────────────────────────────┤
│  Получить входящий платеж по ID                                │
│                                                                │
│  Path Parameters:                                              │
│    payment_id: UUID платежа в МойСклад                         │
│                                                                │
│  Response: PaymentInResponse                                   │
│    {                                                           │
│      "id": "payment_123",                                      │
│      "accountId": "acc_456",                                   │
│      "name": "00042",                                          │
│      "moment": "2024-01-15T10:30:00Z",                         │
│      "applicable": true,                                       │
│      "sum": 10000.0,                                           │
│      "agent": {"meta": {...}},                                 │
│      "organization": {"meta": {...}},                          │
│      "paymentPurpose": "Оплата по счету INV-00042",            │
│      "operations": [                                           │
│        {                                                       │
│          "meta": {"href": ".../customerorder/123", ...},       │
│          "linkedSum": 6000.0                                   │
│        },                                                      │
│        {                                                       │
│          "meta": {"href": ".../customerorder/456", ...},       │
│          "linkedSum": 4000.0                                   │
│        }                                                       │
│      ],                                                        │
│      "meta": {"href": ".../paymentin/payment_123", ...}        │
│    }                                                           │
│                                                                │
│  Используется для:                                             │
│  • Проверки статуса платежа                                    │
│  • Просмотра привязанных документов                            │
│  • Отладки webhook обработки                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2. Доменная модель
```
┌────────────────────────────────────────────────────────────────┐
│                  PaymentInEntity                               │
│              extends BasePaymentEntity                         │
├────────────────────────────────────────────────────────────────┤
│  НЕТ собственных полей - используются только унаследованные:   │
│                                                                │
│  • id: str                                                     │
│  • account_id: str                                             │
│  • name: str                                                   │
│  • moment: datetime                                            │
│  • applicable: bool                                            │
│  • sum: float                                                  │
│  • agent_id: str          ← Покупатель (от кого платеж)        │
│  • organization_id: str   ← Наша организация (кому платеж)     │
│  • payment_purpose: str | None                                 │
│  • linked_operations: list[dict]                               │
│  • meta_href: str                                              │
│  • project_meta_href: str | None                               │
│  • sales_channel_meta_href: str | None                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│              PaymentInFilter (Value Object)                    │
│                    (frozen=True)                               │
├────────────────────────────────────────────────────────────────┤
│  • agent_id: str | None                                        │
│    Фильтр по контрагенту (покупателю)                          │
│                                                                │
│  • sum_value: float | None                                     │
│    Точная сумма для поиска                                     │
│                                                                │
│  • sum_tolerance: float = 0.01                                 │
│    Допуск при сравнении сумм (±1 копейка)                      │
│                                                                │
│  • date_from: datetime | None                                  │
│    Платежи после этой даты                                     │
│                                                                │
│  • date_to: datetime | None                                    │
│    Платежи до этой даты                                        │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  to_moysklad_filter() -> str                                   │
│    Преобразовать в строку фильтра для МойСклад API             │
│                                                                │
│    Пример:                                                     │
│    filter = PaymentInFilter(                                   │
│      agent_id="customer_123",                                  │
│      sum_value=10000.0,                                        │
│      sum_tolerance=0.01                                        │
│    )                                                           │
│    filter.to_moysklad_filter()                                 │
│    # "agent=https://.../counterparty/customer_123;             │
│    #  sum>=9999.99;sum<=10000.01"                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3. Процесс обработки webhook
```
Webhook      PaymentInService   BasePaymentService   МойСклад API
   │                │                   │                   │
   │ {"action":     │                   │                   │
   │  "CREATE",     │                   │                   │
   │  "meta": {     │                   │                   │
   │    "href": ... │                   │                   │
   │  }}            │                   │                   │
   ├───────────────►│                   │                   │
   │                │ get_by_href()     │                   │
   │                ├──────────────────►│                   │
   │                │                   │ GET {href}        │
   │                │                   ├──────────────────►│
   │                │                   │ payment_data      │
   │                │                   │◄──────────────────┤
   │                │ _to_entity()      │                   │
   │                │ (парсинг JSON)    │                   │
   │                │                   │                   │
   │                │ PaymentInEntity   │                   │
   │                │◄──────────────────┤                   │
   │ entity         │                   │                   │
   │◄───────────────┤                   │                   │
   │                │                   │                   │
```

## Особенности реализации
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. МИНИМАЛЬНЫЙ СОБСТВЕННЫЙ КОД                                   ║
║     • PaymentInEntity: pass (0 строк)                             ║
║     • PaymentInClient: entity_type (8 строк)                      ║
║     • PaymentInService: entity_type + _to_entity (~30 строк)      ║
║     • PaymentInResponse: pass (0 строк)                           ║
║     • Исключения: алиасы (0 строк логики)                         ║
║                                                                   ║
║     Собственный код: ~100 строк                                   ║
║     Унаследованный код: ~500 строк                                ║
║     Коэффициент переиспользования: ~83%                           ║
║                                                                   ║
║  2. ЕДИНСТВЕННАЯ СПЕЦИФИКА: ENTITY_TYPE                           ║
║     entity_type = "paymentin"                                     ║
║     Используется для:                                             ║
║     • URL: /entity/paymentin/{id}                                 ║
║     • Метаданные: type="paymentin"                                ║
║                                                                   ║
║  3. PARSING LOGIC В _to_entity()                                  ║
║     • Извлечение ID из href: split("/")[-1]                       ║
║     • Парсинг agent, organization, project, salesChannel          ║
║     • Построение linked_operations                                ║
║                                                                   ║
║  4. VALUE OBJECT С БИЗНЕС-ЛОГИКОЙ                                 ║
║     PaymentInFilter.to_moysklad_filter()                          ║
║     • Единственный value object с методом                         ║
║     • НО: не используется в текущем коде!                         ║
║     • Возможно, для будущего функционала                          ║
║                                                                   ║
║  5. ОДИН REST ENDPOINT                                            ║
║     GET /{payment_id}                                             ║
║     • Для отладки и мониторинга                                   ║
║     • Основная работа через webhook (не через REST)               ║
║                                                                   ║
║  6. НАПРАВЛЕНИЕ ПЛАТЕЖА                                           ║
║     ВХОДЯЩИЙ = от покупателя к нам                                ║
║     • agent_id = покупатель (от кого)                             ║
║     • organization_id = мы (кому)                                 ║
║     • Привязывается к: customerorder, invoiceout, demand          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Получение платежа через REST API
```python
# GET /paymentin/payment_123
response = await client.get("/paymentin/payment_123")

# Response:
{
  "id": "payment_123",
  "name": "00042",
  "sum": 10000.0,
  "paymentPurpose": "Оплата по счету INV-00042",
  "operations": [
    {
      "meta": {"href": ".../customerorder/order_456", "type": "customerorder"},
      "linkedSum": 10000.0
    }
  ]
}
```

### Обработка в webhook handler
```python
from apps.paymentin.services.paymentin_service import PaymentInService
from apps.customerorder.services.customerorder_service import CustomerOrderService

# Webhook payload
webhook_data = {
    "action": "CREATE",
    "events": [{
        "meta": {
            "href": "https://api.moysklad.ru/api/remap/1.2/entity/paymentin/payment_123",
            "type": "paymentin"
        }
    }]
}

# 1. Получить платеж
payment_service = PaymentInService(auth_service)
payment = await payment_service.get_by_href(webhook_data["events"][0]["meta"]["href"])

# payment.sum = 10000.0
# payment.agent_id = "customer_456"
# payment.payment_purpose = "Оплата по счету INV-00042"

# 2. Найти документы для привязки
order_service = CustomerOrderService(auth_service)
orders = await order_service.find_for_payment(
    agent_id=payment.agent_id,
    payment_sum=payment.sum
)

# 3. Привязать платеж к найденным документам
for order in orders:
    payment = await payment_service.link_to_document(
        payment_id=payment.id,
        document_meta_href=order.meta_href,
        linked_sum=order.get_unpaid_amount()
    )
```

### Использование PaymentInFilter
```python
from apps.paymentin.domain.value_objects import PaymentInFilter
from datetime import datetime, timedelta

# Создать фильтр для поиска платежей
filter_obj = PaymentInFilter(
    agent_id="customer_123",
    sum_value=10000.0,
    sum_tolerance=0.01,
    date_from=datetime.now() - timedelta(days=30)
)

# Преобразовать в строку фильтра МойСклад
filter_str = filter_obj.to_moysklad_filter()
# "agent=https://api.moysklad.ru/api/remap/1.2/entity/counterparty/customer_123;
#  sum>=9999.99;sum<=10000.01;moment>=2024-12-23T00:00:00"

# Использовать в API запросе (если бы был метод search)
# payments = await client.search(filter_str=filter_str)
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│                     НАСЛЕДУЕТ ОТ                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  payment_base                                                   │
│    └─► BasePaymentEntity                                        │
│    └─► BasePaymentService<TEntity, TClient>                     │
│    └─► BasePaymentClient                                        │
│    └─► Shared schemas (MetaRef, Agent, etc.)                    │
│    └─► Exception handling                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  РАБОТАЕТ СОВМЕСТНО С                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Документы для входящих платежей:                               │
│  • customerorder - Заказ покупателя (главный)                   │
│  • invoiceout    - Счет покупателю                              │
│  • demand        - Отгрузка                                     │
│                                                                 │
│  Процесс:                                                       │
│  1. paymentin получает платеж из webhook                        │
│  2. customerorder/invoiceout/demand ищутся для привязки         │
│  3. paymentin.link_to_document() привязывает к найденным        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИТ ОТ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ms_auth.MySkladAuthService                                     │
│    └─► Аутентификация для API запросов                          │
│                                                                 │
│  hooks.WebhookHandler                                           │
│    └─► Вызывает PaymentInService при webhook                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Тестирование
```
┌─────────────────────────────────────────────────────────────────┐
│              РЕКОМЕНДУЕМЫЕ СЦЕНАРИИ ТЕСТИРОВАНИЯ                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SERVICE LAYER                                                  │
│  ✓ 1. _to_entity() - полный парсинг данных                      │
│  ✓ 2. _to_entity() - парсинг без project                        │
│  ✓ 3. _to_entity() - парсинг без salesChannel                   │
│  ✓ 4. _to_entity() - пустой массив operations                   │
│  ✓ 5. entity_type возвращает "paymentin"                        │
│                                                                 │
│  CLIENT LAYER                                                   │
│  ✓ 6. entity_type возвращает "paymentin"                        │
│  ✓ 7. Наследованные методы работают (через mock)                │
│                                                                 │
│  API LAYER                                                      │
│  ✓ 8. GET /{payment_id} - успешное получение                    │
│  ✓ 9. GET /{payment_id} - 404 если не найден                    │
│  ✓ 10. Response соответствует PaymentInResponse schema          │
│                                                                 │
│  DOMAIN LAYER                                                   │
│  ✓ 11. PaymentInFilter.to_moysklad_filter() - все поля          │
│  ✓ 12. PaymentInFilter.to_moysklad_filter() - только agent      │
│  ✓ 13. PaymentInFilter.to_moysklad_filter() - sum с tolerance   │
│  ✓ 14. PaymentInFilter.to_moysklad_filter() - date range        │
│  ✓ 15. PaymentInFilter immutable (frozen=True)                  │
│                                                                 │
│  INTEGRATION                                                    │
│  ✓ 16. Webhook → get_by_href → _to_entity                       │
│  ✓ 17. Полный цикл привязки к customerorder                     │
│  ✓ 18. Изоляция по account_id                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Архитектурное решение: тонкий слой