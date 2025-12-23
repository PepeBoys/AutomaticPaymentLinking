# Приложение customerorder - Работа с заказами покупателей

## Описание

Модуль `customerorder` реализует работу с заказами покупателей (customer orders) МойСклад. Приложение построено на базе `payable_document_base` и переиспользует функциональность через наследование. Заказы покупателей используются для учета заказов от клиентов и привязки входящих платежей.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  api.py - REST Endpoints                                           │     │
│  │  • GET /{order_id}          → Получить заказ по ID                 │     │
│  │  • GET /search/for-payment  → Поиск заказов для привязки платежа   │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  CustomerOrderService (extends BaseDocumentService)              │       │
│  │  • get_by_id(order_id)                                           │       │
│  │  • get_by_href(href)                                             │       │
│  │  • find_for_payment(agent_id, payment_sum)                       │       │
│  │  • find_by_name_and_agent(name, agent_id)                        │       │
│  │  • update_state(order_id, state_id)                              │       │
│  │  • get_states()                                                  │       │
│  └────────────────────────────────────────┬─────────────────────────┘       │
│                                           │                                 │
│                                           ▼                                 │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │  CustomerOrderClient (extends BaseDocumentClient)                │       │
│  │  • get(order_id)                                                 │       │
│  │  • get_by_href(href)                                             │       │
│  │  • list(filters)                                                 │       │
│  │  • update(order_id, data)                                        │       │
│  └────────────────────────────────────────┬─────────────────────────┘       │
│                                           │                                 │
│                                           ▼                                 │
│                                   ┌────────────────┐                        │
│                                   │  MySkladAuth   │                        │
│                                   └────────┬───────┘                        │
│                                            │                                │
└────────────────────────────────────────────┼────────────────────────────────┘
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │  МойСклад API          │
                                │  /entity/customerorder │
                                └────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                  НАСЛЕДОВАНИЕ ОТ PAYABLE_DOCUMENT_BASE                     ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  BaseDocumentService            BaseDocumentClient                         ║
║         ▲                                   ▲                              ║
║         │                                   │                              ║
║         │ наследует                         │ наследует                    ║
║         │                                   │                              ║
║  CustomerOrderService              CustomerOrderClient                     ║
║         │                                   │                              ║
║         └───────────────┬───────────────────┘                              ║
║                         │                                                  ║
║                         │ работает с                                       ║
║                         ▼                                                  ║
║              CustomerOrderEntity                                           ║
║        (extends BasePayableDocumentEntity)                                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Основные компоненты

### 1. REST API Endpoints
```
┌────────────────────────────────────────────────────────────────┐
│                     GET /{order_id}                            │
├────────────────────────────────────────────────────────────────┤
│  Получить информацию о заказе покупателя                       │
│                                                                │
│  Path Parameters:                                              │
│    • order_id: str  → ID заказа в МойСклад                     │
│                                                                │
│  Response: CustomerOrderResponse                               │
│    • id: str                                                   │
│    • accountId: str                                            │
│    • name: str                                                 │
│    • moment: datetime                                          │
│    • applicable: bool                                          │
│    • sum: float                                                │
│    • payedSum: float       ← Оплачено                          │
│    • shippedSum: float     ← Отгружено                         │
│    • invoicedSum: float    ← Выставлено счетов                 │
│    • agent: dict                                               │
│    • organization: dict                                        │
│    • meta: MetaRef                                             │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│               GET /search/for-payment                          │
├────────────────────────────────────────────────────────────────┤
│  Поиск заказов для привязки платежа                            │
│                                                                │
│  Query Parameters:                                             │
│    • agent_id: str       → ID контрагента (обязательно)        │
│    • payment_sum: float  → Сумма платежа (обязательно)         │
│    • by_sum: bool        → Искать по точной сумме (default: T) │
│                                                                │
│  Response:                                                     │
│    {                                                           │
│      "orders": [                                               │
│        {                                                       │
│          "id": "...",                                          │
│          "name": "...",                                        │
│          "sum": 15000.0,                                       │
│          "payedSum": 5000.0,                                   │
│          "unpaidAmount": 10000.0,  ← Вычисляется               │
│          "moment": "2024-12-19T10:30:00",                      │
│          "isFullyPaid": false      ← Вычисляется               │
│        }                                                       │
│      ],                                                        │
│      "total": 1                                                │
│    }                                                           │
└────────────────────────────────────────────────────────────────┘
```

### 2. Доменная модель
```
┌────────────────────────────────────────────────────────────────┐
│              BasePayableDocumentEntity                         │
│              (from payable_document_base)                      │
├────────────────────────────────────────────────────────────────┤
│  + id: str                                                     │
│  + account_id: str                                             │
│  + name: str                                                   │
│  + moment: datetime                                            │
│  + applicable: bool                                            │
│  + sum: float                                                  │
│  + payed_sum: float                    ← Оплачено              │
│  + shipped_sum: float | None           ← Отгружено             │
│  + invoiced_sum: float | None          ← Выставлено счетов     │
│  + agent_id: str                                               │
│  + organization_id: str                                        │
│  + meta_href: str                                              │
│  + project_meta_href: str | None                               │
│  + sales_channel_meta_href: str | None                         │
├────────────────────────────────────────────────────────────────┤
│  + get_unpaid_amount() -> float                                │
│      Вычислить неоплаченную сумму (sum - payed_sum)            │
│  + is_fully_paid() -> bool                                     │
│      Проверить, полностью ли оплачен документ                  │
└────────────────────────────────────────────────────────────────┘
                        △
                        │
                        │ extends (без изменений)
                        │
┌────────────────────────────────────────────────────────────────┐
│                 CustomerOrderEntity                            │
├────────────────────────────────────────────────────────────────┤
│  (все поля наследуются от базового класса)                     │
│  (нет дополнительных полей или методов)                        │
└────────────────────────────────────────────────────────────────┘
```

### 3. Value Objects
```
┌────────────────────────────────────────────────────────────────┐
│                 CustomerOrderFilter                            │
│                   (Value Object)                               │
├────────────────────────────────────────────────────────────────┤
│  + agent_id: str | None                                        │
│  + sum_value: float | None                                     │
│  + sum_tolerance: float = 0.01                                 │
│  + date_from: datetime | None                                  │
│  + date_to: datetime | None                                    │
│  + only_unpaid: bool = True        ← Только неоплаченные       │
├────────────────────────────────────────────────────────────────┤
│  + to_moysklad_filter() -> str                                 │
│      Преобразует фильтр в формат API МойСклад                  │
└────────────────────────────────────────────────────────────────┘

ПРИМЕР ИСПОЛЬЗОВАНИЯ:

    filter = CustomerOrderFilter(
        agent_id="agent_123",
        sum_value=15000.0,
        sum_tolerance=1.0,
        only_unpaid=True
    )
    
    filter_str = filter.to_moysklad_filter()
    # "agent=https://...counterparty/agent_123;sum>=14999.0;sum<=15001.0"
```

## Процесс работы

### Получение заказа покупателя
```
  Client              API              Service           Client           МойСклад API
    │                  │                  │                 │                   │
    │  GET /order/123  │                  │                 │                   │
    ├─────────────────►│                  │                 │                   │
    │                  │  get_by_id(123)  │                 │                   │
    │                  ├─────────────────►│                 │                   │
    │                  │                  │  get(123)       │                   │
    │                  │                  ├────────────────►│                   │
    │                  │                  │                 │  GET /order/123   │
    │                  │                  │                 ├──────────────────►│
    │                  │                  │                 │  {order data}     │
    │                  │                  │                 │◄──────────────────┤
    │                  │                  │  order_data     │                   │
    │                  │                  │◄────────────────┤                   │
    │                  │                  │                 │                   │
    │                  │                  │  ┌──────────────────────────┐       │
    │                  │                  │  │ _to_entity(data)         │       │
    │                  │                  │  │ • parse agent_id         │       │
    │                  │                  │  │ • parse organization_id  │       │
    │                  │                  │  │ • parse payed_sum        │       │
    │                  │                  │  │ • parse shipped_sum      │       │
    │                  │                  │  └──────────────────────────┘       │
    │                  │                  │                 │                   │
    │                  │  OrderEntity     │                 │                   │
    │                  │◄─────────────────┤                 │                   │
    │                  │                  │                 │                   │
    │                  │  ┌─────────────────────────────┐   │                   │
    │                  │  │ CustomerOrderResponse       │   │                   │
    │                  │  │ + unpaidAmount вычисляется  │   │                   │
    │                  │  └─────────────────────────────┘   │                   │
    │                  │                  │                 │                   │
    │  OrderResponse   │                  │                 │                   │
    │◄─────────────────┤                  │                 │                   │
    │                  │                  │                 │                   │
```

### Поиск заказов для привязки платежа
```
  Client          API              Service           Client          МойСклад API
    │              │                  │                 │                   │
    │  GET /search │                  │                 │                   │
    │  ?agent=A    │                  │                 │                   │
    │  &sum=15000  │                  │                 │                   │
    ├─────────────►│                  │                 │                   │
    │              │ find_for_payment │                 │                   │
    │              ├─────────────────►│                 │                   │
    │              │                  │                 │                   │
    │              │                  │  ┌──────────────────────────┐       │
    │              │                  │  │ Формирование фильтров:   │       │
    │              │                  │  │ • agent=.../party/A      │       │
    │              │                  │  │ • sum>=14999             │       │
    │              │                  │  │ • sum<=15001             │       │
    │              │                  │  │ • applicable=true        │       │
    │              │                  │  └──────────────────────────┘       │
    │              │                  │                 │                   │
    │              │                  │  list(filters)  │                   │
    │              │                  ├────────────────►│                   │
    │              │                  │                 │  GET /order?filter│
    │              │                  │                 ├──────────────────►│
    │              │                  │                 │  {rows: [...]}    │
    │              │                  │                 │◄──────────────────┤
    │              │                  │  orders_data    │                   │
    │              │                  │◄────────────────┤                   │
    │              │                  │                 │                   │
    │              │                  │  ┌────────────────────────────┐     │
    │              │                  │  │ Фильтрация неоплаченных:   │     │
    │              │                  │  │ [o for o in orders         │     │
    │              │                  │  │  if o.get_unpaid() > 0]    │     │
    │              │                  │  └────────────────────────────┘     │
    │              │                  │                 │                   │
    │              │                  │  ┌────────────────────────────┐     │
    │              │                  │  │ Преобразование в entities  │     │
    │              │                  │  │ [_to_entity(d) for d]      │     │
    │              │                  │  └────────────────────────────┘     │
    │              │                  │                 │                   │
    │              │  [OrderEntity]   │                 │                   │
    │              │◄─────────────────┤                 │                   │
    │              │                  │                 │                   │
    │              │  ┌───────────────────────────────────────┐             │
    │              │  │ Формирование ответа:                  │             │
    │              │  │ • id, name, sum, payedSum             │             │
    │              │  │ • unpaidAmount = get_unpaid_amount()  │             │
    │              │  │ • isFullyPaid = is_fully_paid()       │             │
    │              │  └───────────────────────────────────────┘             │
    │              │                  │                 │                   │
    │  {orders:[]} │                  │                 │                   │
    │◄─────────────┤                  │                 │                   │
    │              │                  │                 │                   │
```

### Привязка платежа к заказу (из WebhookHandler)
```
WebhookHandler      PaymentService    CustomerOrderService   МойСклад API
      │                   │                    │                   │
      │  1. Получить      │                    │                   │
      │     платеж        │                    │                   │
      ├──────────────────►│                    │                   │
      │  payment          │                    │                   │
      │◄──────────────────┤                    │                   │
      │                   │                    │                   │
      │  2. Найти заказ   │                    │                   │
      │     для привязки  │                    │                   │
      ├───────────────────────────────────────►│                   │
      │                   │  find_for_payment  │                   │
      │                   │  (agent, sum)      │                   │
      │                   │                    ├──────────────────►│
      │                   │                    │  GET /order?...   │
      │                   │                    │◄──────────────────┤
      │  [orders]         │                    │                   │
      │◄───────────────────────────────────────┤                   │
      │                   │                    │                   │
      │  3. Привязать     │                    │                   │
      │     платеж к      │                    │                   │
      │     заказу        │                    │                   │
      ├──────────────────►│                    │                   │
      │  link_to_document │                    │                   │
      │  (payment_id,     │                    │                   │
      │   order_href)     │                    │                   │
      │                   ├───────────────────────────────────────►│
      │                   │  PUT /payment/{id} │                   │
      │                   │  {operations:[...]}│                   │
      │                   │◄───────────────────────────────────────┤
      │  success          │                    │                   │
      │◄──────────────────┤                    │                   │
      │                   │                    │                   │
```

## Структура наследования
```
╔═════════════════════════════════════════════════════════════════════════╗
║                    ПОЛНАЯ ИЕРАРХИЯ НАСЛЕДОВАНИЯ                         ║
╠═════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │              payable_document_base (Базовый слой)               │    ║
║  ├─────────────────────────────────────────────────────────────────┤    ║
║  │                                                                 │    ║
║  │  BasePayableDocumentEntity    BaseDocumentService               │    ║
║  │  ┌─────────────────────┐      ┌──────────────────────┐          │    ║
║  │  │ + id                │      │ + get_by_id()        │          │    ║
║  │  │ + name              │      │ + get_by_href()      │          │    ║
║  │  │ + sum               │      │ + find_for_payment() │          │    ║
║  │  │ + payed_sum         │      │ + update_state()     │          │    ║
║  │  │ + shipped_sum       │      │ + get_states()       │          │    ║
║  │  │ + invoiced_sum      │      │ + find_by_name()     │          │    ║
║  │  │ + get_unpaid()      │      └──────────────────────┘          │    ║
║  │  │ + is_fully_paid()   │                 △                     │     ║
║  │  └─────────────────────┘                 │                      │    ║
║  │           △                              │                     │     ║
║  │           │           BaseDocumentClient │                      │    ║
║  │           │           ┌──────────────────┐                      │    ║
║  │           │           │ + get()          │                      │    ║
║  │           │           │ + list()         │                      │    ║
║  │           │           │ + update()       │                      │    ║
║  │           │           └──────────────────┘                      │    ║
║  │           │                    △                               │     ║
║  └───────────┼────────────────────┼────────────────────────────────┘    ║
║              │                    │                                     ║
║              │ extends            │ extends                             ║
║              │                    │                                     ║
║  ┌───────────┼────────────────────┼───────────────────────────────┐     ║
║  │           │  customerorder     │  (Специализация)              │     ║
║  ├───────────┼────────────────────┼───────────────────────────────┤     ║
║  │           │                    │                               │     ║
║  │  CustomerOrderEntity  CustomerOrderService                     │     ║
║  │  ┌─────────────────┐  ┌────────────────────────┐               │     ║
║  │  │ (без изменений) │  │ + entity_type=         │               │     ║
║  │  │                 │  │   "customerorder"      │               │     ║
║  │  │ pass            │  │ + _to_entity()         │               │     ║
║  │  └─────────────────┘  │   специфичный парсинг  │               │     ║
║  │                       └────────────────────────┘               │     ║
║  │                                 │                              │     ║
║  │  CustomerOrderClient            │                              │     ║
║  │  ┌──────────────────────┐       │                              │     ║
║  │  │ + entity_type=       │       │                              │     ║
║  │  │   "customerorder"    │       │                              │     ║
║  │  └──────────────────────┘       │                              │     ║
║  │           │                     │                              │     ║
║  └───────────┼─────────────────────┼──────────────────────────────┘     ║
║              │                     │                                    ║
║              └──────────┬──────────┘                                    ║
║                         │                                               ║
║                         ▼                                               ║
║                 МойСклад API                                            ║
║                 /entity/customerorder                                   ║
║                                                                         ║
╚═════════════════════════════════════════════════════════════════════════╝
```

## Исключения и обработчики
```
┌─────────────────────────────────────────────────────────────────┐
│                   АЛИАСЫ ИСКЛЮЧЕНИЙ                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BaseDocumentException   →  CustomerOrderBaseException          │
│  DocumentAPIError        →  CustomerOrderAPIError               │
│  DocumentNotFoundError   →  CustomerOrderNotFoundError          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 ОБРАБОТЧИКИ ИСКЛЮЧЕНИЙ                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CustomerOrderNotFoundError                                     │
│    → 404 NOT FOUND                                              │
│    → {"detail": "Заказ покупателя не найден"}                   │
│                                                                 │
│  CustomerOrderAPIError                                          │
│    → 502 BAD GATEWAY                                            │
│    → {"detail": "Ошибка API МойСклад"}                          │
│                                                                 │
│  CustomerOrderBaseException                                     │
│    → 500 INTERNAL SERVER ERROR                                  │
│    → {"detail": "Внутренняя ошибка"}                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Dependency Injection
```
                 ┌──────────────────────┐
                 │  get_ms_auth_service │
                 └──────────┬───────────┘
                            │
                            │ Depends
                            │
                            ▼
                 ┌──────────────────────┐
                 │ MySkladAuthService   │
                 └──────────┬───────────┘
                            │
                            │ inject into
                            │
                            ▼
              ┌──────────────────────────────┐
              │ get_customerorder_service    │
              └──────────┬───────────────────┘
                         │
                         │ returns
                         │
                         ▼
              ┌──────────────────────────────┐
              │  CustomerOrderService        │
              └──────────┬───────────────────┘
                         │
                         │ Annotated as
                         │
                         ▼
              ┌──────────────────────────────┐
              │  CustomerOrderSvcDep         │
              │  (Type Alias)                │
              └──────────────────────────────┘
```

## Примеры использования

### Получить заказ покупателя по ID
```http
GET /customerorder/550e8400-e29b-41d4-a716-446655440000
Authorization: Basic <credentials>

Response 200:
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "accountId": "account_123",
    "name": "00042",
    "moment": "2024-12-15T14:20:00",
    "applicable": true,
    "sum": 25000.0,
    "payedSum": 10000.0,
    "shippedSum": 0.0,
    "invoicedSum": 25000.0,
    "agent": {
        "meta": {
            "href": "entity/counterparty/agent_456",
            "type": "counterparty"
        }
    },
    "organization": {
        "meta": {
            "href": "entity/organization/org_789",
            "type": "organization"
        }
    },
    "meta": {
        "href": "entity/customerorder/550e8400-e29b-41d4-a716-446655440000",
        "type": "customerorder"
    }
}
```

### Поиск заказов для привязки платежа
```http
GET /customerorder/search/for-payment?agent_id=agent_456&payment_sum=15000&by_sum=true
Authorization: Basic <credentials>

Response 200:
{
    "orders": [
        {
            "id": "order_123",
            "name": "00042",
            "sum": 25000.0,
            "payedSum": 10000.0,
            "unpaidAmount": 15000.0,
            "moment": "2024-12-15T14:20:00",
            "isFullyPaid": false
        },
        {
            "id": "order_124",
            "name": "00043",
            "sum": 15000.0,
            "payedSum": 0.0,
            "unpaidAmount": 15000.0,
            "moment": "2024-12-16T10:00:00",
            "isFullyPaid": false
        }
    ],
    "total": 2
}
```

### Использование из WebhookHandler
```python
# Поиск заказов для привязки платежа
orders = await customerorder_service.find_for_payment(
    agent_id="agent_456",
    payment_sum=15000.0,
    search_by_sum=True,
    organization_id="org_789",
    prioritize_oldest=True
)

# Привязка платежа к заказу
await paymentin_service.link_to_document(
    payment_id="payment_123",
    document_meta_href="entity/customerorder/order_456",
    linked_sum=15000.0
)

# Обновление статуса заказа
await customerorder_service.update_state(
    document_id="order_123",
    state_id="state_success"
)

# Поиск заказа по имени и контрагенту
order = await customerorder_service.find_by_name_and_agent(
    name="00042",
    agent_id="agent_456",
    organization_id="org_789"
)
```

### Использование CustomerOrderFilter
```python
from apps.customerorder.domain.value_objects import CustomerOrderFilter
from datetime import datetime, timedelta

# Создать фильтр
filter = CustomerOrderFilter(
    agent_id="agent_456",
    sum_value=25000.0,
    sum_tolerance=1.0,
    date_from=datetime.now() - timedelta(days=30),
    date_to=datetime.now(),
    only_unpaid=True  # Только неоплаченные
)

# Преобразовать в строку для API
filter_string = filter.to_moysklad_filter()
# "agent=https://...counterparty/agent_456;sum>=24999.0;sum<=25001.0;moment>=...;moment<=..."
```

## Интеграция с системой webhook
```
┌────────────────────────────────────────────────────────────────┐
│              РОЛЬ В АВТОМАТИЧЕСКОЙ ПРИВЯЗКЕ                    │
└────────────────────────────────────────────────────────────────┘

WebhookHandler при обработке ВХОДЯЩИХ платежей:

1. Получает платеж (paymentin/cashin) через PaymentService
2. Ищет подходящие заказы через CustomerOrderService
3. Привязывает платеж к заказам
4. Применяет статусы к платежу и заказам (опционально)
5. Переносит проект и канал продаж (опционально)

┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  МойСклад → Webhook → WebhookService → WebhookHandler           │
│                                               │                 │
│                          ┌────────────────────┼────────────┐    │
│                          │                    │            │    │
│                          ▼                    ▼            ▼    │
│                   PaymentService    CustomerOrderService  ...   │
│                     (paymentin)            │                    │
│                          │                 │                    │
│                          ▼                 ▼                    │
│                    get_by_href()    find_for_payment()          │
│                          │                 │                    │
│                          ▼                 ▼                    │
│                   PaymentEntity    [CustomerOrderEntity]        │
│                          │                 │                    │
│                          └────────┬────────┘                    │
│                                   │                             │
│                                   ▼                             │
│                         link_to_document()                      │
│                         update_states()                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Различия между типами документов
```
╔═══════════════════════════════════════════════════════════════════╗
║              ДОКУМЕНТЫ ДЛЯ ВХОДЯЩИХ VS ИСХОДЯЩИХ                  ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ВХОДЯЩИЕ ПЛАТЕЖИ (paymentin, cashin):                            ║
║  ┌──────────────────────────────────────────────────────────┐     ║
║  │ customerorder  → Заказ покупателя                        │     ║
║  │ invoiceout     → Счет покупателю                         │     ║
║  │ demand         → Отгрузка покупателю                     │     ║
║  └──────────────────────────────────────────────────────────┘     ║
║                                                                   ║
║  ИСХОДЯЩИЕ ПЛАТЕЖИ (paymentout, cashout):                         ║
║  ┌──────────────────────────────────────────────────────────┐     ║
║  │ purchaseorder  → Заказ поставщику                        │     ║
║  │ invoicein      → Счет от поставщика                      │     ║
║  │ supply         → Приемка от поставщика                   │     ║
║  └──────────────────────────────────────────────────────────┘     ║
║                                                                   ║
║  ОБЩИЕ ХАРАКТЕРИСТИКИ ДОКУМЕНТОВ:                                 ║
║  • sum           → Общая сумма документа                          ║
║  • payed_sum     → Оплачено по документу                          ║
║  • shipped_sum   → Отгружено (для заказов и счетов)               ║
║  • invoiced_sum  → Выставлено счетов (для заказов)                ║
║                                                                   ║
║  МЕТОДЫ:                                                          ║
║  • get_unpaid_amount() → sum - payed_sum                          ║
║  • is_fully_paid()     → payed_sum >= sum                         ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Особенности реализации
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. НАСЛЕДОВАНИЕ ОТ PAYABLE_DOCUMENT_BASE                         ║
║     В отличие от платежей (payment_base), заказы наследуют        ║
║     от payable_document_base, что дает:                           ║
║     • payed_sum, shipped_sum, invoiced_sum                        ║
║     • get_unpaid_amount(), is_fully_paid()                        ║
║     • find_for_payment(), find_by_name_and_agent()                ║
║                                                                   ║
║  2. ДОПОЛНИТЕЛЬНЫЙ ENDPOINT ДЛЯ ПОИСКА                            ║
║     GET /search/for-payment позволяет:                            ║
║     • Найти заказы по контрагенту и сумме                         ║
║     • Получить детальную информацию:                              ║
║       - unpaidAmount (вычисляется)                                ║
║       - isFullyPaid (вычисляется)                                 ║
║     • Использовать для UI списка заказов                          ║
║                                                                   ║
║  3. МИНИМУМ СОБСТВЕННОГО КОДА                                     ║
║     Файл                         Строк кода                       ║
║     ──────────────────────────   ─────────                        ║
║     api.py                          70                            ║
║     dependencies.py                 22                            ║
║     domain/entities.py               8                            ║
║     domain/value_objects.py         42                            ║
║     exceptions.py                    9                            ║
║     exception_handlers.py           14                            ║
║     schemas.py                       6                            ║
║     services/client.py               8                            ║
║     services/service.py             60                            ║
║     ────────────────────────────────                              ║
║     ИТОГО:                         ~240 строк                     ║
║                                                                   ║
║  4. ИСПОЛЬЗОВАНИЕ ДОМЕННЫХ МЕТОДОВ В API                          ║
║     API endpoint /search/for-payment использует:                  ║
║     • entity.get_unpaid_amount()                                  ║
║     • entity.is_fully_paid()                                      ║
║     Это правильный подход - бизнес-логика в domain layer          ║
║                                                                   ║
║  5. ВАЛИДАЦИЯ В _TO_ENTITY                                        ║
║     ```python                                                     ║
║     if not data.get("meta", {}).get("href"):                      ║
║         raise CustomerOrderNotFoundError(...)                     ║
║     ```                                                           ║
║     Проверка обязательных полей при парсинге                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИМОСТИ МОДУЛЯ                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  payable_document_base                                          │
│    └─► Базовые классы для всех платёжных документов             │
│        • BasePayableDocumentEntity                              │
│        • BaseDocumentService                                    │
│        • BaseDocumentClient                                     │
│                                                                 │
│  ms_auth                                                        │
│    └─► Аутентификация в МойСклад API                            │
│        • MySkladAuthService                                     │
│        • get_account_id()                                       │
│        • get_basic_auth_header()                                │
│                                                                 │
│  hooks                                                          │
│    └─► Использует CustomerOrderService в WebhookHandler         │
│        • Поиск заказов для привязки входящих платежей           │
│        • Обновление статусов заказов                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 SIBLING МОДУЛИ (аналогичные)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ДОКУМЕНТЫ ДЛЯ ВХОДЯЩИХ ПЛАТЕЖЕЙ:                               │
│  • customerorder  → Заказ покупателя                            │
│  • invoiceout     → Счет покупателю                             │
│  • demand         → Отгрузка                                    │
│                                                                 │
│  ДОКУМЕНТЫ ДЛЯ ИСХОДЯЩИХ ПЛАТЕЖЕЙ:                              │
│  • purchaseorder  → Заказ поставщику                            │
│  • invoicein      → Счет поставщика                             │
│  • supply         → Приемка                                     │
│                                                                 │
│  Все имеют идентичную структуру и API                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              ИСПОЛЬЗУЕТСЯ ПЛАТЕЖНЫМИ МОДУЛЯМИ                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  paymentin (входящие платежи):                                  │
│    • Ищет customerorder через find_for_payment()                │
│    • Привязывается через link_to_document()                     │
│                                                                 │
│  cashin (приходные ордера):                                     │
│    • Ищет customerorder через find_for_payment()                │
│    • Привязывается через link_to_document()                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Тестирование
```
┌─────────────────────────────────────────────────────────────────┐
│              РЕКОМЕНДУЕМЫЕ СЦЕНАРИИ ТЕСТИРОВАНИЯ                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  API ENDPOINTS                                                  │
│  ✓ 1. GET /{order_id} - успешное получение                      │
│  ✓ 2. GET /{order_id} - заказ не найден (404)                   │
│  ✓ 3. GET /{order_id} - ошибка API МойСклад (502)               │
│  ✓ 4. GET /search/for-payment - поиск по сумме                  │
│  ✓ 5. GET /search/for-payment - поиск без суммы                 │
│  ✓ 6. GET /search/for-payment - нет подходящих заказов          │
│                                                                 │
│  SERVICE LAYER                                                  │
│  ✓ 7. get_by_id() - корректное преобразование в entity          │
│  ✓ 8. get_by_href() - получение по прямой ссылке                │
│  ✓ 9. find_for_payment() - поиск с точной суммой                │
│  ✓ 10. find_for_payment() - поиск по контрагенту                │
│  ✓ 11. find_for_payment() - фильтрация неоплаченных             │
│  ✓ 12. find_by_name_and_agent() - поиск по имени                │
│  ✓ 13. update_state() - изменение статуса                       │
│  ✓ 14. get_states() - получение списка статусов                 │
│                                                                 │
│  DOMAIN LAYER                                                   │
│  ✓ 15. CustomerOrderEntity.get_unpaid_amount()                  │
│  ✓ 16. CustomerOrderEntity.is_fully_paid() - полностью оплачен  │
│  ✓ 17. CustomerOrderEntity.is_fully_paid() - частично оплачен   │
│  ✓ 18. CustomerOrderFilter.to_moysklad_filter()                 │
│  ✓ 19. Парсинг agent_id из href                                 │
│  ✓ 20. Парсинг organization_id из href                          │
│  ✓ 21. Валидация отсутствия meta.href                           │
│                                                                 │
│  INTEGRATION                                                    │
│  ✓ 22. Полный цикл webhook: payment → find order → link         │
│  ✓ 23. Привязка платежа к частично оплаченному заказу           │
│  ✓ 24. Привязка нескольких платежей к одному заказу             │
│  ✓ 25. Изоляция по account_id                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MOCK ДАННЫЕ:

┌─ Заказ покупателя ──────────────────────────────────────────────┐
│  {                                                              │
│    "id": "order_123",                                           │
│    "accountId": "account_456",                                  │
│    "name": "00042",                                             │
│    "moment": "2024-12-15T14:20:00",                             │
│    "applicable": true,                                          │
│    "sum": 25000.0,                                              │
│    "payedSum": 10000.0,       ← Частично оплачен                │
│    "shippedSum": 0.0,                                           │
│    "invoicedSum": 25000.0,                                      │
│    "agent": {                                                   │
│      "meta": {                                                  │
│        "href": ".../counterparty/agent_789",                    │
│        "type": "counterparty"                                   │
│      }                                                          │
│    },                                                           │
│    "organization": {                                            │
│      "meta": {                                                  │
│        "href": ".../organization/org_111",                      │
│        "type": "organization"                                   │
│      }                                                          │
│    },                                                           │
│    "meta": {                                                    │
│      "href": ".../customerorder/order_123",                     │
│      "type": "customerorder"                                    │
│    }                                                            │
│  }                                                              │
│                                                                 │
│  entity.get_unpaid_amount() → 15000.0                           │
│  entity.is_fully_paid()     → False                             │
└─────────────────────────────────────────────────────────────────┘
```