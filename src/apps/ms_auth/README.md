# path: src/apps/ms_auth/README.md
# Приложение ms_auth - Аутентификация в МойСклад API

## Описание

Модуль `ms_auth` реализует систему аутентификации для работы с МойСклад API. Поддерживает два режима: Basic Auth (login/password) и Bearer Auth (access token из Vendor API). Обеспечивает multi-tenancy с изоляцией по account_id.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                      │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  api.py - REST Endpoints                                           │     │
│  │  • GET  /credentials  → Получить текущие credentials (без пароля)  │     │
│  │  • POST /credentials  → Установить/обновить credentials            │     │
│  └────────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY INJECTION                               │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  dependencies.py                                                 │      │
│  │  • get_ms_auth_service()                                         │      │
│  │    Автоматическое разрешение account_id:                         │      │
│  │    1. X-Account-Id header                                        │      │
│  │    2. request.state.ms_account_id (webhook)                      │      │
│  │    3. Единственный активный аккаунт                              │      │
│  │                                                                  │      │
│  │  • get_ms_auth_service_for_account(account_id)                   │      │
│  │    Явное указание account_id для Vendor API                      │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            SERVICE LAYER                                   │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  MySkladAuthService                                              │      │
│  │  • set_credentials(creds)    → Basic Auth setup                  │      │
│  │  • get_credentials()         → Получить без пароля               │      │
│  │  • set_access_token(token)   → Bearer Auth setup                 │      │
│  │  • get_basic_auth_header()   → Authorization header              │      │
│  │  • get_base_url()            → URL МойСклад API                  │      │
│  │  • get_account_id()          → Текущий account_id                │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  build_ms_auth_service() - Factory                               │      │
│  │  Создает независимый экземпляр для каждого запроса               │      │
│  │  (решение проблемы multi-tenancy)                                │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  MySkladCredentials (Entity)                                     │      │
│  │  • login: str                                                    │      │
│  │  • password: str                                                 │      │
│  │  • base_url: HttpUrl                                             │      │
│  │  • get_basic_auth_token() -> str                                 │      │
│  │  • to_dict_safe() -> dict                                        │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  BasicAuthHeader (Value Object)                                  │      │
│  │  • token: str                                                    │      │
│  │  • to_dict() -> dict                                             │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                      ДВА РЕЖИМА АУТЕНТИФИКАЦИИ                             ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  1. BASIC AUTH (login/password)                                            ║
║     • Для разработки и отладки                                             ║
║     • Credentials из ENV или API                                           ║
║     • Authorization: Basic <base64(login:password)>                        ║
║                                                                            ║
║  2. BEARER AUTH (access token)                                             ║
║     • Для production (Vendor API)                                          ║
║     • Access token из vendor_account table                                 ║
║     • Authorization: Bearer <access_token>                                 ║
║     • Приоритетнее Basic Auth                                              ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Основные компоненты

### 1. REST API Endpoints
```
┌────────────────────────────────────────────────────────────────┐
│                    GET /credentials                            │
├────────────────────────────────────────────────────────────────┤
│  Получить текущие настройки доступа (без пароля)               │
│                                                                │
│  Response: MySkladCredentialsOut | null                        │
│    {                                                           │
│      "login": "admin@company",                                 │
│      "base_url": "https://api.moysklad.ru/api/remap/1.2",      │
│      "has_password": true                                      │
│    }                                                           │
│                                                                │
│  Если credentials не установлены → null                        │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   POST /credentials                            │
├────────────────────────────────────────────────────────────────┤
│  Установить/обновить credentials                               │
│                                                                │
│  Request: MySkladCredentialsIn                                 │
│    {                                                           │
│      "login": "admin@company",                                 │
│      "password": "secretpass",                                 │
│      "base_url": "https://api.moysklad.ru/api/remap/1.2"       │
│    }                                                           │
│                                                                │
│  Валидация:                                                    │
│    • login: минимум 3 символа, не пустой                       │
│    • password: минимум 6 символов, не пустой                   │
│    • base_url: валидный HttpUrl                                │
│                                                                │
│  Response 201: MySkladCredentialsOut                           │
└────────────────────────────────────────────────────────────────┘
```

### 2. Dependency Injection
```
┌────────────────────────────────────────────────────────────────┐
│             get_ms_auth_service(request, ...)                  │
│                                                                │
│  Автоматическое разрешение account_id:                         │
│                                                                │
│  1️⃣  X-Account-Id header (приоритет)                           │
│      Явное указание клиентом                                   │
│                                                                │
│  2️⃣  request.state.ms_account_id                               │
│      Из webhook payload (установлено middleware)               │
│                                                                │
│  3️⃣  Единственный активный аккаунт                             │
│      Если установлена только одна компания                     │
│                                                                │
│  Если 2+ компании и нет явного указания:                       │
│    → 400 BAD REQUEST (требуется X-Account-Id)                  │
│                                                                │
│  Если нет активных аккаунтов:                                  │
│    → 401 UNAUTHORIZED                                          │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│        get_ms_auth_service_for_account(account_id)             │
│                                                                │
│  Явное указание account_id для Vendor API endpoints            │
│                                                                │
│  • Используется в activate/deactivate endpoints                │
│  • Исключает fallback на "дефолтный" аккаунт                   │
│  • Строгая проверка существования и активности                 │
└────────────────────────────────────────────────────────────────┘
```

### 3. Доменная модель
```
┌────────────────────────────────────────────────────────────────┐
│                  MySkladCredentials                            │
│                      (Entity)                                  │
├────────────────────────────────────────────────────────────────┤
│  + login: str                                                  │
│  + password: str                                               │
│  + base_url: HttpUrl                                           │
├────────────────────────────────────────────────────────────────┤
│  + get_basic_auth_token() -> str                               │
│      Генерирует base64(login:password)                         │
│                                                                │
│  + to_dict_safe() -> dict                                      │
│      Возвращает данные БЕЗ пароля                              │
│      {"login": "...", "base_url": "...", "has_password": true} │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  BasicAuthHeader                               │
│                  (Value Object)                                │
├────────────────────────────────────────────────────────────────┤
│  + token: str  (base64 encoded)                                │
├────────────────────────────────────────────────────────────────┤
│  + to_dict() -> dict                                           │
│      {"Authorization": "Basic <token>"}                        │
└────────────────────────────────────────────────────────────────┘
```

### 4. Сервисный слой
```
┌────────────────────────────────────────────────────────────────┐
│                  MySkladAuthService                            │
├────────────────────────────────────────────────────────────────┤
│  Внутреннее состояние:                                         │
│  • _credentials: MySkladCredentials | None                     │
│  • _access_token: str | None                                   │
│  • _base_url: str | None                                       │
│  • _account_id: str | None                                     │
├────────────────────────────────────────────────────────────────┤
│  Методы управления credentials:                                │
│  • set_credentials(creds)                                      │
│  • get_credentials() -> MySkladCredentialsOut | None           │
│  • get_raw_credentials() -> MySkladCredentials | None          │
│                                                                │
│  Методы управления access token:                               │
│  • set_access_token(token, base_url, account_id)               │
│  • clear_access_token()                                        │
│                                                                │
│  Методы получения данных:                                      │
│  • get_basic_auth_header() -> dict | None                      │
│    Приоритет: Bearer > Basic                                   │
│  • get_base_url() -> str                                       │
│  • get_account_id() -> str | None                              │
│                                                                │
│  Внутренние методы:                                            │
│  • _load_from_env()  (fallback для разработки)                 │
│  • _ensure_loaded()  (lazy loading)                            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│             build_ms_auth_service() - Factory                  │
├────────────────────────────────────────────────────────────────┤
│  Создает независимый экземпляр MySkladAuthService              │
│                                                                │
│  Решение проблемы multi-tenancy:                               │
│  • Раньше: синглтон → race condition при 2+ аккаунтах          │
│  • Сейчас: factory → каждый запрос = свой экземпляр            │
│                                                                │
│  Используется в:                                               │
│  • get_ms_auth_service()                                       │
│  • get_ms_auth_service_for_account()                           │
└────────────────────────────────────────────────────────────────┘
```

## Процесс работы

### Разрешение account_id для запроса
```
  Request            Middleware         Dependencies         Database          AuthService
    │                    │                    │                   │                  │
    │  HTTP Request      │                    │                   │                  │
    ├───────────────────►│                    │                   │                  │
    │                    │                    │                   │                  │
    │                    │  ┌────────────────────────────────┐    │                  │
    │                    │  │ Проверить источник account_id: │    │                  │
    │                    │  │ 1. X-Account-Id header?        │    │                  │
    │                    │  │ 2. request.state.ms_account_id?│    │                  │
    │                    │  │ 3. Единственный активный?      │    │                  │
    │                    │  └────────────────────────────────┘    │                  │
    │                    │                    │                   │                  │
    │                    │  get_ms_auth_service()                 │                  │
    │                    ├───────────────────►│                   │                  │
    │                    │                    │                   │                  │
    │                    │                    │  Если нет явного: │                  │
    │                    │                    │  list_active(2)   │                  │
    │                    │                    ├──────────────────►│                  │
    │                    │                    │  [accounts]       │                  │
    │                    │                    │◄──────────────────┤                  │
    │                    │                    │                   │                  │
    │                    │                    │  ┌─────────────────────────────┐     │
    │                    │                    │  │ len == 0: 401 UNAUTHORIZED  │     │
    │                    │                    │  │ len == 1: use this account  │     │
    │                    │                    │  │ len >= 2: 400 BAD REQUEST   │     │
    │                    │                    │  └─────────────────────────────┘     │
    │                    │                    │                   │                  │
    │                    │                    │  get_by_account_id│                  │
    │                    │                    ├──────────────────►│                  │
    │                    │                    │  account          │                  │
    │                    │                    │◄──────────────────┤                  │
    │                    │                    │                   │                  │
    │                    │                    │  build_ms_auth_service()             │
    │                    │                    ├─────────────────────────────────────►│
    │                    │                    │  auth_service     │                  │
    │                    │                    │◄─────────────────────────────────────┤
    │                    │                    │                   │                  │
    │                    │                    │  set_access_token(│                  │
    │                    │                    │    token,         │                  │
    │                    │                    │    base_url,      │                  │
    │                    │                    │    account_id     │                  │
    │                    │                    │  )                │                  │
    │                    │                    ├─────────────────────────────────────►│
    │                    │                    │                   │                  │
    │                    │  auth_service      │                   │                  │
    │                    │◄───────────────────┤                   │                  │
    │  auth_service      │                    │                   │                  │
    │◄───────────────────┤                    │                   │                  │
    │                    │                    │                   │                  │
```

### Использование в API клиентах
```
  PaymentClient     MySkladAuthService     МойСклад API
       │                    │                    │
       │  get_payment(id)   │                    │
       ├──────────────────► │                    │
       │                    │                    │
       │  headers = get_basic_auth_header()      │
       ├───────────────────►│                    │
       │                    │                    │
       │                    │  ┌─────────────────────────────┐
       │                    │  │ Приоритет:                  │
       │                    │  │ 1. Bearer (access_token)    │
       │                    │  │ 2. Basic (login:password)   │
       │                    │  └─────────────────────────────┘
       │                    │                    │
       │  {"Authorization": "Bearer <token>"}    │
       │◄───────────────────┤                    │
       │                    │                    │
       │  GET /entity/paymentin/{id}             │
       │  Authorization: Bearer <token>          │
       ├────────────────────────────────────────►│
       │                    │  payment_data      │
       │◄────────────────────────────────────────┤
       │                    │                    │
```

### Factory Pattern для multi-tenancy
```
╔════════════════════════════════════════════════════════════════════════════╗
║                  ПРОБЛЕМА СИНГЛТОНА (СТАРЫЙ ПОДХОД)                        ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Было: Глобальный синглтон auth_service                                    ║
║                                                                            ║
║  Request 1: activate_app(account_id="A")                                   ║
║    → auth_service.set_access_token(token_A, account_id="A")                ║
║                                                                            ║
║  Request 2: activate_app(account_id="B")  (параллельно!)                   ║
║    → auth_service.set_access_token(token_B, account_id="B")                ║
║      ❌ ПЕРЕЗАПИСАЛ токен Request 1!                                       ║
║                                                                            ║
║  Request 1 продолжает работу:                                              ║
║    → get_basic_auth_header()                                               ║
║    → Возвращает token_B вместо token_A                                     ║
║    → ❌ ОШИБКА: доступ к чужим данным!                                     ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════════════╗
║                   РЕШЕНИЕ: FACTORY (НОВЫЙ ПОДХОД)                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  Сейчас: Каждый запрос получает свой экземпляр                             ║
║                                                                            ║
║  Request 1:                                                                ║
║    → auth_service_1 = build_ms_auth_service()                              ║
║    → auth_service_1.set_access_token(token_A, account_id="A")              ║
║                                                                            ║
║  Request 2:  (параллельно!)                                                ║
║    → auth_service_2 = build_ms_auth_service()                              ║
║    → auth_service_2.set_access_token(token_B, account_id="B")              ║
║                                                                            ║
║  Request 1 продолжает работу:                                              ║
║    → auth_service_1.get_basic_auth_header()                                ║
║    → ✓ Возвращает token_A (свой токен)                                     ║
║                                                                            ║
║  Request 2 продолжает работу:                                              ║
║    → auth_service_2.get_basic_auth_header()                                ║
║    → ✓ Возвращает token_B (свой токен)                                     ║
║                                                                            ║
║  ✓ Изоляция по account_id достигнута!                                      ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Использование в API клиентах
```python
from apps.ms_auth.dependencies import AuthSvcDep
from fastapi import APIRouter

router = APIRouter()

@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    auth_service: AuthSvcDep,  # Автоматическое разрешение account_id
):
    """Получить платеж с автоматической аутентификацией."""
    # auth_service уже настроен с правильным account_id и access_token
    
    headers = auth_service.get_basic_auth_header()
    base_url = auth_service.get_base_url()
    account_id = auth_service.get_account_id()
    
    # Использовать в HTTP клиенте
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/entity/paymentin/{payment_id}",
            headers=headers
        )
    
    return response.json()
```

### Явное указание account_id через header
```http
GET /api/payments/123
X-Account-Id: account_456
Authorization: Bearer <optional>

# auth_service будет настроен для account_456
```

### Vendor API endpoints
```python
from apps.ms_auth.dependencies import get_ms_auth_service_for_account

@router.post("/vendor/activate/{account_id}")
async def activate_app(
    account_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Активация для конкретного account_id."""
    # Строгая привязка к переданному account_id
    auth_service = await get_ms_auth_service_for_account(account_id, session)
    
    # Работа с этим конкретным аккаунтом
    base_url = auth_service.get_base_url()
    # ...
```

### Работа с credentials (Basic Auth)
```python
from apps.ms_auth.schemas import MySkladCredentialsIn

# Установить credentials
creds = MySkladCredentialsIn(
    login="admin@company",
    password="secretpass",
    base_url="https://api.moysklad.ru/api/remap/1.2"
)
auth_service.set_credentials(creds)

# Получить credentials без пароля
creds_out = auth_service.get_credentials()
# {"login": "admin@company", "base_url": "...", "has_password": true}

# Получить auth header
headers = auth_service.get_basic_auth_header()
# {"Authorization": "Basic YWRtaW5AY29tcGFueTpzZWNyZXRwYXNz"}
```

### Работа с access token (Bearer Auth)
```python
# Установить access token (например, после активации в Vendor API)
auth_service.set_access_token(
    token="jwt_access_token_here",
    base_url="https://api.moysklad.ru/api/remap/1.2",
    account_id="account_123"
)

# Получить auth header
headers = auth_service.get_basic_auth_header()
# {"Authorization": "Bearer jwt_access_token_here"}
# ← Bearer приоритетнее Basic!

# Очистить token
auth_service.clear_access_token()
```

## Особенности реализации
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. ДВА РЕЖИМА АУТЕНТИФИКАЦИИ                                     ║
║     • Basic Auth: для разработки, из ENV или API                  ║
║     • Bearer Auth: для production, из vendor_account table        ║
║     • Bearer приоритетнее Basic                                   ║
║                                                                   ║
║  2. MULTI-TENANCY                                                 ║
║     • Factory pattern вместо синглтона                            ║
║     • Каждый запрос = свой экземпляр auth_service                 ║
║     • Изоляция по account_id                                      ║
║                                                                   ║
║  3. АВТОМАТИЧЕСКОЕ РАЗРЕШЕНИЕ ACCOUNT_ID                          ║
║     Приоритет:                                                    ║
║     1. X-Account-Id header (явное указание)                       ║
║     2. request.state.ms_account_id (webhook)                      ║
║     3. Единственный активный аккаунт                              ║
║                                                                   ║
║     Если 2+ аккаунта и нет явного → 400 BAD REQUEST               ║
║                                                                   ║
║  4. LAZY LOADING CREDENTIALS                                      ║
║     • Credentials загружаются из ENV при первом обращении         ║
║     • _ensure_loaded() вызывается перед каждым get_*()            ║
║     • Fallback для разработки                                     ║
║                                                                   ║
║  5. БЕЗОПАСНОСТЬ                                                  ║
║     • Пароль никогда не возвращается в API responses              ║
║     • to_dict_safe() скрывает пароль                              ║
║     • Credentials хранятся только в памяти (не БД)                ║
║                                                                   ║
║  6. ВАЛИДАЦИЯ                                                     ║
║     • Login: минимум 3 символа                                    ║
║     • Password: минимум 6 символов                                ║
║     • base_url: валидный HttpUrl                                  ║
║                                                                   ║
║  7. VALUE OBJECTS                                                 ║
║     • BasicAuthHeader - immutable value object                    ║
║     • to_dict() для преобразования в HTTP header                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Архитектурные решения

### Почему Factory вместо Singleton?
```
╔═══════════════════════════════════════════════════════════════════╗
║            ЭВОЛЮЦИЯ АРХИТЕКТУРЫ: СИНГЛТОН → FACTORY               ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ПРОБЛЕМА: Race condition в синглтоне                             ║
║                                                                   ║
║  Thread 1: activate_app(account="A") → set_access_token(token_A)  ║
║  Thread 2: activate_app(account="B") → set_access_token(token_B)  ║
║  Thread 1: делает API call → использует token_B вместо token_A ❌║
║                                                                   ║
║  РЕШЕНИЕ: Factory pattern                                         ║
║                                                                   ║
║  • build_ms_auth_service() создает новый экземпляр                ║
║  • Каждый запрос получает свой auth_service                       ║
║  • Полная изоляция между запросами                                ║
║  • Нет shared state                                               ║
║                                                                   ║
║  TRADE-OFF:                                                       ║
║  • Плюс: Изоляция, thread-safety                                  ║
║  • Минус: Больше аллокаций памяти                                 ║
║  • Вердикт: Правильное решение для multi-tenancy                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

### Почему credentials в памяти, а не в БД?
```
╔═══════════════════════════════════════════════════════════════════╗
║         CREDENTIALS: MEMORY vs DATABASE                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ТЕКУЩИЙ ПОДХОД: In-memory (только для Basic Auth)                ║
║                                                                   ║
║  Причины:                                                         ║
║  1. Basic Auth используется только для разработки                 ║
║  2. Production работает через Bearer Auth (токены в БД)           ║
║  3. Credentials из ENV как fallback                               ║
║  4. Упрощение архитектуры                                         ║
║                                                                   ║
║  PRODUCTION: Bearer Auth через vendor_account table               ║
║                                                                   ║
║  • access_token хранится в БД                                     ║
║  • account_id для изоляции                                        ║
║  • is_active для контроля доступа                                 ║
║                                                                   ║
║  БУДУЩЕЕ: Если потребуется персистентность Basic Auth             ║
║  → Добавить таблицу ms_credentials с шифрованием паролей          ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│                     ИСПОЛЬЗУЕТСЯ В                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ВСЕ клиенты МойСклад API:                                      │
│  • payment_base.BasePaymentClient                               │
│  • payable_document_base.BaseDocumentClient                     │
│  • hooks.WebhookService                                         │
│                                                                 │
│  Vendor API:                                                    │
│  • vendor_api.api (activate/deactivate)                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     ЗАВИСИТ ОТ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  vendor_api.VendorAccountRepository                             │
│    └─► Загрузка access_token и account_id из БД                 │
│                                                                 │
│  core.config.settings                                           │
│    └─► MS_LOGIN, MS_PASSWORD, MS_BASE_URL (fallback)            │
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
│  ✓ 1. set_credentials() - установка credentials                 │
│  ✓ 2. get_credentials() - получение без пароля                  │
│  ✓ 3. get_basic_auth_header() - Basic Auth header               │
│  ✓ 4. set_access_token() - установка Bearer token               │
│  ✓ 5. get_basic_auth_header() - Bearer приоритетнее Basic       │
│  ✓ 6. clear_access_token() - очистка токена                     │
│  ✓ 7. get_base_url() - получение URL                            │
│  ✓ 8. get_account_id() - получение account_id                   │
│  ✓ 9. _load_from_env() - загрузка из ENV                        │
│                                                                 │
│  DOMAIN LAYER                                                   │
│  ✓ 10. MySkladCredentials.get_basic_auth_token()                │
│  ✓ 11. MySkladCredentials.to_dict_safe() - без пароля           │
│  ✓ 12. BasicAuthHeader.to_dict()                                │
│                                                                 │
│  DEPENDENCY INJECTION                                           │
│  ✓ 13. get_ms_auth_service() - X-Account-Id header              │
│  ✓ 14. get_ms_auth_service() - request.state.ms_account_id      │
│  ✓ 15. get_ms_auth_service() - единственный аккаунт             │
│  ✓ 16. get_ms_auth_service() - 2+ аккаунта без header (400)    │
│  ✓ 17. get_ms_auth_service() - нет активных аккаунтов (401)    │
│  ✓ 18. get_ms_auth_service_for_account() - явный account_id    │
│                                                                 │
│  API ENDPOINTS                                                  │
│  ✓ 19. GET /credentials - с credentials                         │
│  ✓ 20. GET /credentials - без credentials (null)                │
│  ✓ 21. POST /credentials - валидные данные                      │
│  ✓ 22. POST /credentials - невалидный login (400)               │
│  ✓ 23. POST /credentials - короткий password (400)              │
│                                                                 │
│  MULTI-TENANCY                                                  │
│  ✓ 24. Параллельные запросы с разными account_id                │
│  ✓ 25. Factory создает независимые экземпляры                   │
│  ✓ 26. Изоляция access_token между запросами                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Миграция со старого подхода
```
╔═══════════════════════════════════════════════════════════════════╗
║              BREAKING CHANGES: СИНГЛТОН → FACTORY                 ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  СТАРЫЙ КОД (НЕ РАБОТАЕТ):                                        ║
║                                                                   ║
║  from apps.ms_auth.services.auth_service import ms_auth_service   ║
║  # ❌ Глобальный синглтон больше не существует                    ║
║                                                                   ║
║  ms_auth_service.set_access_token(token)                          ║
║  # ❌ Будет перезаписан следующим запросом                        ║
║                                                                   ║
║  НОВЫЙ КОД (ПРАВИЛЬНО):                                           ║
║                                                                   ║
║  from apps.ms_auth.dependencies import AuthSvcDep                 ║
║                                                                   ║
║  @router.get("/endpoint")                                         ║
║  async def endpoint(auth_service: AuthSvcDep):                    ║
║      # ✓ Свой экземпляр для этого запроса                         ║
║      headers = auth_service.get_basic_auth_header()               ║
║                                                                   ║
║  МИГРАЦИЯ:                                                        ║
║  1. Заменить прямой импорт на AuthSvcDep                          ║
║  2. Использовать DI во всех endpoints                             ║
║  3. Убрать глобальное состояние                                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```