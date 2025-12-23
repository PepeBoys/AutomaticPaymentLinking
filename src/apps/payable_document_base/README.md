# Базовый модуль payable_document_base - Оплачиваемые документы

## Описание

Модуль `payable_document_base` предоставляет базовую функциональность для всех документов МойСклад, которые могут получать платежи. Это фундаментальный модуль, от которого наследуются customerorder, invoiceout, demand (для входящих платежей), purchaseorder, invoicein, supply (для исходящих платежей).

**Важно**: Это **базовый модуль** без собственных REST API endpoints. Он предоставляет только базовые классы, методы и утилиты для наследования.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           БАЗОВЫЙ МОДУЛЬ                                    │
│                    (БЕЗ REST API, ТОЛЬКО БАЗОВЫЕ КЛАССЫ)                    │
└─────────────────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════════════╗
║                        DOMAIN LAYER (BASE)                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌────────────────────────────────────────────────────────────────┐       ║
║  │           BasePayableDocumentEntity                            │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  Базовая сущность для всех оплачиваемых документов             │       ║
║  │  • id, account_id, name, moment, applicable                    │       ║
║  │  • sum, payed_sum, agent_id, organization_id                   │       ║
║  │  • shipped_sum, invoiced_sum (optional)                        │       ║
║  │  • meta_href, project_meta_href, sales_channel_meta_href       │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  Domain методы:                                                │       ║
║  │  • is_fully_paid() -> bool                                     │       ║
║  │  • is_partially_paid() -> bool                                 │       ║
║  │  • get_unpaid_amount() -> float                                │       ║
║  │  • matches_sum(payment_sum, tolerance) -> bool                 │       ║
║  │  • matches_unpaid_sum(payment_sum, tolerance) -> bool          │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                              △                                            ║
║                              │ наследуют                                  ║
║                              │                                            ║
║  ┌───────────────────────────┴────────────────────────────────────┐       ║
║  │                                                                │       ║
║  │  InvoiceOutEntity    CustomerOrderEntity    DemandEntity       │       ║
║  │  InvoiceInEntity     PurchaseOrderEntity    SupplyEntity       │       ║
║  │                                                                │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
║  ┌────────────────────────────────────────────────────────────────┐       ║
║  │              BaseDocumentFilter (Value Object)                 │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  • agent_id: str | None                                        │       ║
║  │  • organization_id: str | None                                 │       ║
║  │  • date_from: datetime | None                                  │       ║
║  │  • prioritize_oldest: bool                                     │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════╗
║                        SERVICE LAYER (BASE)                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌────────────────────────────────────────────────────────────────┐       ║
║  │  BaseDocumentService<TEntity, TClient>  (Generic)              │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  Бизнес-логика работы с документами                            │       ║
║  │                                                                │       ║
║  │  • find_for_payment(agent_id, sum, ...)                        │       ║
║  │    Найти документы для привязки платежа                        │       ║
║  │                                                                │       ║
║  │  • find_by_name_and_agent(name, agent_id, ...)                 │       ║
║  │    Найти документ по номеру и контрагенту                      │       ║
║  │                                                                │       ║
║  │  • update_state(document_id, state_id)                         │       ║
║  │    Обновить статус документа                                   │       ║
║  │                                                                │       ║
║  │  • get_by_id(document_id)                                      │       ║
║  │    Получить документ по ID                                     │       ║
║  │                                                                │       ║
║  │  • get_states()                                                │       ║
║  │    Получить список статусов                                    │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                              △                                            ║
║                              │ наследуют                                  ║
║                              │                                            ║
║  ┌───────────────────────────┴────────────────────────────────────┐       ║
║  │                                                                │       ║
║  │  InvoiceOutService    CustomerOrderService    DemandService    │       ║
║  │  InvoiceInService     PurchaseOrderService    SupplyService    │       ║
║  │                                                                │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════╗
║                        CLIENT LAYER (BASE)                                ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌────────────────────────────────────────────────────────────────┐       ║
║  │              BaseDocumentClient (ABC)                          │       ║
║  ├────────────────────────────────────────────────────────────────┤       ║
║  │  Работа с МойСклад API для документов                          │       ║
║  │                                                                │       ║
║  │  • search(filter_str, limit, offset, order)                    │       ║
║  │    Поиск документов с фильтрами                                │       ║
║  │                                                                │       ║
║  │  • search_by_agent_and_sum(agent_id, sum, ...)                 │       ║
║  │    Поиск по контрагенту и сумме (точное совпадение)            │       ║
║  │                                                                │       ║
║  │  • search_by_agent(agent_id, organization_id, ...)             │       ║
║  │    Поиск по контрагенту (все документы)                        │       ║
║  │                                                                │       ║
║  │  • get_by_id(document_id, expand)                              │       ║
║  │    Получить документ по ID                                     │       ║
║  │                                                                │       ║
║  │  • get_states()                                                │       ║
║  │    Получить метаданные статусов                                │       ║
║  │                                                                │       ║
║  │  • update_state(document_id, state_id)                         │       ║
║  │    Обновить статус документа                                   │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                              △                                            ║
║                              │ наследуют                                  ║
║                              │                                            ║
║  ┌───────────────────────────┴────────────────────────────────────┐       ║
║  │                                                                │       ║
║  │  InvoiceOutClient    CustomerOrderClient    DemandClient       │       ║
║  │  InvoiceInClient     PurchaseOrderClient    SupplyClient       │       ║
║  │                                                                │       ║
║  └────────────────────────────────────────────────────────────────┘       ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                    EXCEPTION HANDLING                                      ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  BaseDocumentException  →  500 INTERNAL_SERVER_ERROR                       ║
║  DocumentNotFoundError  →  404 NOT_FOUND                                   ║
║  DocumentAPIError       →  502 BAD_GATEWAY                                 ║
║                                                                            ║
║  Exception handlers:                                                       ║
║  • base_document_exception_handler                                         ║
║  • document_not_found_handler                                              ║
║  • document_api_error_handler                                              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Основные компоненты

### 1. Доменная модель
```
┌────────────────────────────────────────────────────────────────┐
│           BasePayableDocumentEntity                            │
├────────────────────────────────────────────────────────────────┤
│  Обязательные поля:                                            │
│  • id: str                    - UUID документа                 │
│  • account_id: str            - ID учетной записи              │
│  • name: str                  - Номер документа                │
│  • moment: datetime           - Дата документа                 │
│  • applicable: bool           - Проведен ли документ           │
│  • sum: float                 - Общая сумма                    │
│  • payed_sum: float           - Оплаченная сумма               │
│  • agent_id: str              - Контрагент (покупатель/        │
│                                 поставщик)                     │
│  • organization_id: str       - Организация (наша компания)    │
│  • meta_href: str             - Ссылка на документ в API       │
│                                                                │
│  Опциональные поля:                                            │
│  • project_meta_href: str | None      - Ссылка на проект       │
│  • sales_channel_meta_href: str | None - Канал продаж          │
│  • shipped_sum: float | None          - Сумма отгруженного     │
│  • invoiced_sum: float | None         - Сумма выставленного    │
├────────────────────────────────────────────────────────────────┤
│  Domain методы:                                                │
│                                                                │
│  is_fully_paid() -> bool                                       │
│    Проверить полную оплату (payed_sum >= sum)                  │
│                                                                │
│  is_partially_paid() -> bool                                   │
│    Проверить частичную оплату (0 < payed_sum < sum)            │
│                                                                │
│  get_unpaid_amount() -> float                                  │
│    Получить неоплаченную сумму (max(0, sum - payed_sum))       │
│                                                                │
│  matches_sum(payment_sum, tolerance=0.01) -> bool              │
│    Проверить точное совпадение суммы документа                 │
│                                                                │
│  matches_unpaid_sum(payment_sum, tolerance=0.01) -> bool       │
│    Проверить совпадение неоплаченной суммы                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│              BaseDocumentFilter                                │
│              (Value Object)                                    │
├────────────────────────────────────────────────────────────────┤
│  • agent_id: str | None                                        │
│    Фильтр по контрагенту                                       │
│                                                                │
│  • organization_id: str | None                                 │
│    Фильтр по организации                                       │
│                                                                │
│  • date_from: datetime | None                                  │
│    Фильтр по дате (документы после date_from)                  │
│                                                                │
│  • prioritize_oldest: bool = True                              │
│    Приоритет старых документов                                 │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 2. Сервисный слой
```
┌────────────────────────────────────────────────────────────────┐
│     BaseDocumentService<TEntity, TClient>                      │
│                  (Generic Abstract Base)                       │
├────────────────────────────────────────────────────────────────┤
│  Абстрактные методы (требуют реализации):                      │
│                                                                │
│  entity_type() -> str                                          │
│    Тип сущности ("invoiceout", "customerorder", ...)           │
│                                                                │
│  _to_entity(data: dict) -> TEntity                             │
│    Преобразование JSON из API в доменную сущность              │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Унаследованные методы (готовые к использованию):              │
│                                                                │
│  find_for_payment(                                             │
│    agent_id: str,                                              │
│    payment_sum: float,                                         │
│    search_by_sum: bool = True,                                 │
│    organization_id: str | None = None,                         │
│    prioritize_oldest: bool = True                              │
│  ) -> List[TEntity]                                            │
│                                                                │
│    Найти документы для привязки платежа                        │
│                                                                │
│    Логика:                                                     │
│    1. search_by_sum=True:                                      │
│       • Поиск по точной сумме (± tolerance)                    │
│       • Фильтр payed_sum = 0 (неоплаченные)                    │
│                                                                │
│    2. search_by_sum=False:                                     │
│       • Поиск по контрагенту за последние 60 дней              │
│       • Фильтр not is_fully_paid()                             │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  find_by_name_and_agent(                                       │
│    name: str,                                                  │
│    agent_id: str,                                              │
│    organization_id: str | None = None,                         │
│    moment: datetime | None = None,                             │
│    prioritize_oldest: bool = True                              │
│  ) -> TEntity                                                  │
│                                                                │
│    Найти документ по номеру и контрагенту                      │
│    (используется для парсинга назначения платежа)              │
│                                                                │
│    Throws: DocumentNotFoundError если не найден                │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_state(                                                 │
│    document_id: str,                                           │
│    state_id: str                                               │
│  ) -> TEntity                                                  │
│                                                                │
│    Обновить статус документа                                   │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_by_id(document_id: str) -> TEntity                        │
│                                                                │
│    Получить документ по идентификатору                         │
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
│              BaseDocumentClient (ABC)                          │
├────────────────────────────────────────────────────────────────┤
│  Абстрактные методы:                                           │
│                                                                │
│  entity_type() -> str                                          │
│    Тип сущности для URL API                                    │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  Унаследованные методы:                                        │
│                                                                │
│  search(                                                       │
│    filter_str: str | None,                                     │
│    limit: int = 100,                                           │
│    offset: int = 0,                                            │
│    order: str | None = None                                    │
│  ) -> List[dict]                                               │
│                                                                │
│    Универсальный поиск документов                              │
│                                                                │
│    Фильтры (примеры):                                          │
│    • "agent=.../counterparty/{id}"                             │
│    • "sum>=1000;sum<=2000"                                     │
│    • "moment>=2024-01-01 00:00:00"                             │
│    • "payedSum<sum"                                            │
│                                                                │
│    Сортировка:                                                 │
│    • "moment,asc" - по дате возрастанию                        │
│    • "moment,desc" - по дате убыванию                          │
│                                                                │
│    Retry: 3 попытки с exponential backoff (2-10 сек)           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  search_by_agent_and_sum(                                      │
│    agent_id: str,                                              │
│    sum_value: float,                                           │
│    tolerance: float = 0.01,                                    │
│    organization_id: str | None,                                │
│    prioritize_oldest: bool = True                              │
│  ) -> List[dict]                                               │
│                                                                │
│    Поиск по контрагенту и точной сумме                         │
│                                                                │
│    Фильтр:                                                     │
│    • agent={agent_id}                                          │
│    • sum>={sum_value - tolerance}                              │
│    • sum<={sum_value + tolerance}                              │
│    • organization={organization_id} (опционально)              │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  search_by_agent(                                              │
│    agent_id: str,                                              │
│    organization_id: str | None,                                │
│    date_from: datetime | None,                                 │
│    limit: int = 100,                                           │
│    order: str | None,                                          │
│    only_unpaid: bool = False                                   │
│  ) -> List[dict]                                               │
│                                                                │
│    Поиск всех документов контрагента                           │
│                                                                │
│    Фильтры:                                                    │
│    • agent={agent_id}                                          │
│    • moment>={date_from} (МСК timezone!)                       │
│    • payedSum<sum (только неоплаченные)                        │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_by_id(                                                    │
│    document_id: str,                                           │
│    expand: str | None = None                                   │
│  ) -> dict                                                     │
│                                                                │
│    Получить документ по ID                                     │
│    expand: "agent,organization" для раскрытия связей           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  get_states() -> list[dict]                                    │
│                                                                │
│    GET /entity/{type}/metadata                                 │
│    Получить метаданные статусов                                │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  update_state(                                                 │
│    document_id: str,                                           │
│    state_id: str                                               │
│  ) -> dict                                                     │
│                                                                │
│    PUT /entity/{type}/{document_id}                            │
│    Обновить статус документа                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Процесс работы

### Поиск документов для привязки платежа
```
WebhookHandler   DocumentService   BaseDocumentService   BaseDocumentClient   МойСклад API
     │                 │                   │                    │                   │
     │  find_for_      │                   │                    │                   │
     │  payment()      │                   │                    │                   │
     ├────────────────►│                   │                    │                   │
     │                 │  find_for_payment()                    │                   │
     │                 ├──────────────────►│                    │                   │
     │                 │                   │                    │                   │
     │                 │                   │  ┌─────────────────────────────────┐   │
     │                 │                   │  │ Если search_by_sum=True:        │   │
     │                 │                   │  │ • Поиск по точной сумме         │   │
     │                 │                   │  │ • Фильтр payed_sum=0            │   │
     │                 │                   │  │                                 │   │
     │                 │                   │  │ Если search_by_sum=False:       │   │
     │                 │                   │  │ • Поиск по контрагенту          │   │
     │                 │                   │  │ • За последние 60 дней          │   │
     │                 │                   │  │ • Фильтр not is_fully_paid()    │   │
     │                 │                   │  └─────────────────────────────────┘   │
     │                 │                   │                    │                   │
     │                 │                   │  search_by_agent_and_sum()             │
     │                 │                   ├───────────────────►│                   │
     │                 │                   │                    │ GET /entity/{type}│
     │                 │                   │                    ├──────────────────►│
     │                 │                   │                    │  ?filter=...      │
     │                 │                   │                    │  ?order=moment,asc│
     │                 │                   │                    │  {rows: [...]}    │
     │                 │                   │                    │◄──────────────────┤
     │                 │                   │  [documents_data]  │                   │
     │                 │                   │◄───────────────────┤                   │
     │                 │                   │                    │                   │
     │                 │                   │  ┌──────────────────────────────────┐  │
     │                 │                   │  │ Преобразование в entities:       │  │
     │                 │                   │  │ [_to_entity(d) for d in data]    │  │
     │                 │                   │  │                                  │  │
     │                 │                   │  │ Фильтрация:                      │  │
     │                 │                   │  │ • search_by_sum: payed_sum = 0   │  │
     │                 │                   │  │ • else: not is_fully_paid()      │  │
     │                 │                   │  └──────────────────────────────────┘  │
     │                 │                   │                    │                   │
     │                 │  [TEntity]        │                    │                   │
     │                 │◄──────────────────┤                    │                   │
     │  [documents]    │                   │                    │                   │
     │◄────────────────┤                   │                    │                   │
     │                 │                   │                    │                   │
```

### Обновление статуса документа
```
WebhookHandler   DocumentService   BaseDocumentClient   МойСклад API
     │                  │                   │                   │
     │  update_state()  │                   │                   │
     ├─────────────────►│                   │                   │
     │                  │  update_state()   │                   │
     │                  ├──────────────────►│                   │
     │                  │                   │  PUT /entity/{type}/{id}
     │                  │                   │  {state: {meta: {...}}}
     │                  │                   ├──────────────────►│
     │                  │                   │  updated_document │
     │                  │                   │◄──────────────────┤
     │                  │  _to_entity()     │                   │
     │                  │  TEntity          │                   │
     │                  │◄──────────────────┤                   │
     │  entity          │                   │                   │
     │◄─────────────────┤                   │                   │
     │                  │                   │                   │
```

## Особенности реализации
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. GENERIC ТИПЫ                                                  ║
║     BaseDocumentService<TEntity, TClient>                         ║
║     • TEntity: bound=BasePayableDocumentEntity                    ║
║     • TClient: bound=BaseDocumentClient                           ║
║     • Строгая типизация наследников                               ║
║                                                                   ║
║  2. RETRY МЕХАНИЗМ                                                ║
║     @retry(                                                       ║
║       stop=stop_after_attempt(3),                                 ║
║       wait=wait_exponential(multiplier=1, min=2, max=10)          ║
║     )                                                             ║
║     • Exponential backoff: 2s, 4s, 8s                             ║
║     • Применяется к search() методу                               ║
║                                                                   ║
║  3. MOSCOW TIMEZONE (МСК = UTC+3)                                 ║
║     МойСклад API требует даты в МСК timezone:                     ║
║     msk_tz = timezone(timedelta(hours=3))                         ║
║     date_msk = date_from.astimezone(msk_tz)                       ║
║     format: "YYYY-MM-DD HH:MM:SS"                                 ║
║                                                                   ║
║  4. TOLERANCE ДЛЯ СРАВНЕНИЯ СУММ                                  ║
║     • По умолчанию: ±0.01 (1 копейка)                             ║
║     • matches_sum(payment_sum, tolerance=0.01)                    ║
║     • Учитывает floating point errors                             ║
║                                                                   ║
║  5. ФИЛЬТРАЦИЯ ДОКУМЕНТОВ                                         ║
║     Формат МойСклад API:                                          ║
║     • Разделитель: ";" (AND)                                      ║
║     • agent=https://api.moysklad.ru/.../counterparty/{id}         ║
║     • sum>=1000;sum<=2000                                         ║
║     • moment>=2024-01-01 00:00:00                                 ║
║     • payedSum<sum                                                ║
║                                                                   ║
║  6. DOMAIN METHODS                                                ║
║     Бизнес-логика в entity:                                       ║
║     • is_fully_paid() - проверка полной оплаты                    ║
║     • get_unpaid_amount() - расчет остатка                        ║
║     • matches_sum() - сравнение с tolerance                       ║
║                                                                   ║
║  7. ДВУХЭТАПНАЯ ФИЛЬТРАЦИЯ                                        ║
║     1. API фильтры (МойСклад)                                     ║
║     2. Domain фильтры (Python)                                    ║
║     Пример: payed_sum = 0 фильтруется в Python                    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Создание наследника Entity
```python
from dataclasses import dataclass
from apps.payable_document_base.domain.entities import BasePayableDocumentEntity

@dataclass
class InvoiceOutEntity(BasePayableDocumentEntity):
    """Счет покупателю - наследует все поля и методы."""
    pass  # Можно добавить дополнительные поля если нужно

# Использование domain методов
invoice = InvoiceOutEntity(
    id="inv_123",
    sum=10000.0,
    payed_sum=3000.0,
    # ... остальные поля
)

invoice.is_fully_paid()  # False
invoice.is_partially_paid()  # True
invoice.get_unpaid_amount()  # 7000.0
invoice.matches_sum(10000.0)  # True
invoice.matches_unpaid_sum(7000.0)  # True
```

### Создание наследника Service
```python
from apps.payable_document_base.services.base_service import BaseDocumentService
from apps.payable_document_base.services.base_client import BaseDocumentClient

class InvoiceOutService(BaseDocumentService[InvoiceOutEntity, InvoiceOutClient]):
    """Сервис для счетов покупателям."""
    
    def __init__(self, auth_service: MySkladAuthService) -> None:
        super().__init__(auth_service, InvoiceOutClient(auth_service))
    
    @property
    def entity_type(self) -> str:
        """Тип сущности в МойСклад API."""
        return "invoiceout"
    
    @staticmethod
    def _to_entity(data: dict) -> InvoiceOutEntity:
        """Преобразовать JSON в entity."""
        # Парсинг полей из data
        return InvoiceOutEntity(
            id=data["id"],
            account_id=data["accountId"],
            # ... остальные поля
        )

# Использование унаследованных методов
service = InvoiceOutService(auth_service)

# Поиск документов для платежа
invoices = await service.find_for_payment(
    agent_id="customer_123",
    payment_sum=10000.0,
    search_by_sum=True,  # Точное совпадение суммы
    organization_id="org_456"
)

# Поиск документа по номеру
invoice = await service.find_by_name_and_agent(
    name="INV-00042",
    agent_id="customer_123"
)

# Обновление статуса
await service.update_state(
    document_id="inv_123",
    state_id="state_paid"
)
```

### Создание наследника Client
```python
from apps.payable_document_base.services.base_client import BaseDocumentClient

class InvoiceOutClient(BaseDocumentClient):
    """Клиент для счетов покупателям."""
    
    @property
    def entity_type(self) -> str:
        """Тип сущности для URL."""
        return "invoiceout"

# Использование унаследованных методов
client = InvoiceOutClient(auth_service)

# Поиск по фильтру
documents = await client.search(
    filter_str="agent=.../counterparty/123;sum>=1000",
    order="moment,desc",
    limit=10
)

# Поиск по контрагенту и сумме
documents = await client.search_by_agent_and_sum(
    agent_id="customer_123",
    sum_value=10000.0,
    tolerance=0.01
)

# Получение по ID
document = await client.get_by_id("inv_123", expand="agent,organization")
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│              ИСПОЛЬЗУЕТСЯ В (НАСЛЕДНИКИ)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ДОКУМЕНТЫ ДЛЯ ВХОДЯЩИХ ПЛАТЕЖЕЙ:                               │
│  • customerorder  - Заказ покупателя (REST API)                 │
│  • invoiceout     - Счет покупателю (internal)                  │
│  • demand         - Отгрузка (internal)                         │
│                                                                 │
│  ДОКУМЕНТЫ ДЛЯ ИСХОДЯЩИХ ПЛАТЕЖЕЙ:                              │
│  • purchaseorder  - Заказ поставщику                            │
│  • invoicein      - Счет поставщика (internal)                  │
│  • supply         - Приемка (internal)                          │
│                                                                 │
│  Все эти модули наследуют:                                      │
│  • BasePayableDocumentEntity                                    │
│  • BaseDocumentService<TEntity, TClient>                        │
│  • BaseDocumentClient                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИТ ОТ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ms_auth.MySkladAuthService                                     │
│    └─► Аутентификация для API запросов                          │
│                                                                 │
│  payment_base.schemas                                           │
│    └─► MetaRef, Agent, Organization (shared schemas)            │
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
```

## Тестирование
```
┌─────────────────────────────────────────────────────────────────┐
│              РЕКОМЕНДУЕМЫЕ СЦЕНАРИИ ТЕСТИРОВАНИЯ                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DOMAIN LAYER                                                   │
│  ✓ 1. is_fully_paid() - payed_sum >= sum                        │
│  ✓ 2. is_fully_paid() - payed_sum < sum                         │
│  ✓ 3. is_partially_paid() - 0 < payed_sum < sum                 │
│  ✓ 4. is_partially_paid() - payed_sum = 0                       │
│  ✓ 5. get_unpaid_amount() - positive                            │
│  ✓ 6. get_unpaid_amount() - zero                                │
│  ✓ 7. matches_sum() - точное совпадение                         │
│  ✓ 8. matches_sum() - с tolerance                               │
│  ✓ 9. matches_unpaid_sum() - частичная оплата                   │
│                                                                 │
│  CLIENT LAYER                                                   │
│  ✓ 10. search() - успешный запрос                               │
│  ✓ 11. search() - с фильтрами                                   │
│  ✓ 12. search() - с сортировкой                                 │
│  ✓ 13. search_by_agent_and_sum() - точная сумма                 │
│  ✓ 14. search_by_agent_and_sum() - с tolerance                  │
│  ✓ 15. search_by_agent() - базовый поиск                        │
│  ✓ 16. search_by_agent() - с date_from                          │
│  ✓ 17. search_by_agent() - only_unpaid=True                     │
│  ✓ 18. get_by_id() - успешное получение                         │
│  ✓ 19. get_by_id() - с expand                                   │
│  ✓ 20. get_states() - получение метаданных                      │
│  ✓ 21. update_state() - обновление статуса                      │
│  ✓ 22. Retry mechanism - 3 попытки                              │
│  ✓ 23. HTTPStatusError обработка                                │
│                                                                 │
│  SERVICE LAYER                                                  │
│  ✓ 24. find_for_payment() - search_by_sum=True                  │
│  ✓ 25. find_for_payment() - search_by_sum=False                 │
│  ✓ 26. find_for_payment() - фильтр payed_sum=0                  │
│  ✓ 27. find_for_payment() - фильтр is_fully_paid()              │
│  ✓ 28. find_by_name_and_agent() - найден                        │
│  ✓ 29. find_by_name_and_agent() - не найден (exc)               │
│  ✓ 30. find_by_name_and_agent() - с moment фильтром             │
│                                                                 │
│  EXCEPTION HANDLING                                             │
│  ✓ 31. DocumentNotFoundError - 404                              │
│  ✓ 32. DocumentAPIError - 502                                   │
│  ✓ 33. BaseDocumentException - 500                              │
│                                                                 │
│  TIMEZONE HANDLING                                              │
│  ✓ 34. Moscow timezone конвертация                              │
│  ✓ 35. Формат даты "YYYY-MM-DD HH:MM:SS"                        │
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
║  • 6 документов (customerorder, invoiceout, demand, ...)          ║
║  • Каждый реализует похожую логику                                ║
║  • Дублирование кода: search(), update_state(), get_by_id()       ║
║  • Дублирование domain методов: is_fully_paid(), get_unpaid()     ║
║  • Несогласованность в разных модулях                             ║
║  • Сложность поддержки: изменения в 6 местах                      ║
║                                                                   ║
║  РЕШЕНИЕ: БАЗОВЫЙ МОДУЛЬ                                          ║
║                                                                   ║
║  Преимущества:                                                    ║
║  1. DRY - код написан один раз                                    ║
║  2. Consistency - все документы работают одинаково                ║
║  3. Maintainability - изменения в одном месте                     ║
║  4. Testability - тесты базового модуля покрывают всех            ║
║  5. Extensibility - легко добавить новый тип документа            ║
║                                                                   ║
║  Недостатки (trade-offs):                                         ║
║  1. Сложность понимания для новых разработчиков                   ║
║  2. Generic типы могут быть непривычны                            ║
║  3. Иерархия наследования требует дисциплины                      ║
║                                                                   ║
║  ВЕРДИКТ: Правильное решение для 6+ похожих модулей               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```