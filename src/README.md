# main.py - Точка входа FastAPI приложения

## Описание

Файл `main.py` является **точкой входа** всего приложения. Здесь происходит инициализация FastAPI, настройка middleware, регистрация роутеров и exception handlers, подключение статических файлов и templates.

**Ключевое назначение**: Сборка всех компонентов приложения в единое целое и запуск FastAPI сервера.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI APPLICATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  1. LIFESPAN - Управление жизненным циклом                         │     │
│  │  @asynccontextmanager                                              │     │
│  │  async def lifespan(app):                                          │     │
│  │      await init_db()  ← Инициализация БД при старте                │     │
│  │      yield                                                         │     │
│  │      # cleanup при остановке (пока пусто)                          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  2. MIDDLEWARE - Обработка запросов                                │     │
│  │  • CORSMiddleware       - CORS headers                             │     │
│  │  • Rate Limit Middleware - Ограничение запросов (опционально)      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  3. EXCEPTION HANDLERS - Централизованная обработка ошибок         │     │
│  │  • HOOKS_EXCEPTION_HANDLERS                                        │     │
│  │  • CUSTOMERORDER_EXCEPTION_HANDLERS                                │     │
│  │  • CASHIN_EXCEPTION_HANDLERS                                       │     │
│  │  • PAYMENTIN_EXCEPTION_HANDLERS                                    │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  4. STATIC FILES & TEMPLATES                                       │     │
│  │  • /static - StaticFiles(directory="src/static")                   │     │
│  │  • templates - Jinja2Templates(directory="src/templates")          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  5. ROUTERS - API endpoints                                        │     │
│  │  • /api/auth/ms         - ms_auth (OAuth МойСклад)                 │     │
│  │  • /api                 - vendor_api (Vendor API МойСклад)         │     │
│  │  • /api/hooks           - hooks (Вебхуки управление)               │     │
│  │  • /api/customerorder   - customerorder (Заказы покупателей)       │     │
│  │  • /api/cashin          - cashin (Приходные ордера)                │     │
│  │  • /api/paymentin       - paymentin (Входящие платежи)             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  6. HOME PAGE - Главная страница                                   │     │
│  │  • GET / - HTML страница с UI приложения                           │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Lifespan Management
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    await init_db()  # Инициализация БД
    
    yield  # Приложение работает
    
    # Shutdown (пока пусто)
    # TODO: Cleanup ресурсов

app = FastAPI(
    title="МС: Автоматическая привязка платежей",
    lifespan=lifespan,
)
```

**Что происходит**:
- При старте: `init_db()` - создание таблиц и применение миграций
- При работе: приложение обрабатывает запросы
- При остановке: cleanup (пока не реализован)

### 2. CORS Middleware
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # Из .env
    allow_credentials=True,
    allow_methods=["*"],  # Все HTTP методы
    allow_headers=["*"],  # Все headers
)
```

**Назначение**: Разрешить cross-origin запросы из веб-интерфейса

**Настройка**:
```ini
# .env
APL_ALLOWED_ORIGINS=["http://localhost:3000", "https://your-domain.com"]
```

### 3. Rate Limiting Middleware
```python
if settings.api_rate_limit > 0:
    rate_limit_window = 60  # 60 секунд
    rate_limit_counters: dict[str, tuple[float, int]] = {}
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        client_host = request.client.host
        now = time.time()
        window_start, count = rate_limit_counters.get(client_host, (now, 0))
        
        # Новое окно?
        if now - window_start >= rate_limit_window:
            window_start, count = now, 0
        
        count += 1
        rate_limit_counters[client_host] = (window_start, count)
        
        # Превышен лимит?
        if count > settings.api_rate_limit:
            return PlainTextResponse("Rate limit exceeded", status_code=429)
        
        return await call_next(request)
```

**Как работает**:
- Считает запросы от каждого IP
- Окно: 60 секунд
- Лимит: `settings.api_rate_limit` запросов в окно
- При превышении: 429 Too Many Requests

**Настройка**:
```ini
# .env
APL_API_RATE_LIMIT=100  # 100 запросов в минуту
APL_API_RATE_LIMIT=0    # Отключить rate limiting
```

### 4. Exception Handlers
```python
# Регистрация exception handlers из каждого модуля
for exc_class, handler in HOOKS_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

for exc_class, handler in CUSTOMERORDER_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)

# ... и так далее для каждого модуля
```

**Что происходит**:
- Каждый модуль экспортирует `EXCEPTION_HANDLERS`
- main.py регистрирует их в FastAPI
- При возникновении исключения вызывается соответствующий handler
- Handler преобразует исключение в HTTP response

**Пример**:
```python
# hooks/exception_handlers.py
async def webhook_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Webhook not found"},
    )

EXCEPTION_HANDLERS = {
    WebhookNotFoundError: webhook_not_found_handler,
}

# main.py регистрирует это автоматически
```

### 5. Static Files & Templates
```python
# Статические файлы (CSS, JS, images)
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="src/templates")

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = {
        "request": request,
        "page_title": "Автоматическая привязка платежей",
    }
    return templates.TemplateResponse("index.html", context)
```

**Структура**:
```
src/
├── static/           ← CSS, JS, images
│   ├── css/
│   ├── js/
│   └── img/
└── templates/        ← HTML templates
    └── index.html
```

**Доступ**:
- Static files: `http://localhost:8000/static/css/style.css`
- Home page: `http://localhost:8000/`

### 6. Routers Registration
```python
app.include_router(ms_auth_router, prefix="/api/auth/ms", tags=["ms_auth"])
app.include_router(vendor_api_router, prefix="/api", tags=["vendor_api"])
app.include_router(hooks_router, prefix="/api/hooks", tags=["hooks"])
app.include_router(customerorder_router, prefix="/api/customerorder", tags=["customerorder"])
app.include_router(cashin_router, prefix="/api/cashin", tags=["cashin"])
app.include_router(paymentin_router, prefix="/api/paymentin", tags=["paymentin"])
```

**API Structure**:
```
/api/auth/ms
├── GET  /login        - Начать OAuth flow
└── GET  /callback     - OAuth callback

/api
├── PUT    /moysklad/vendor/1.0/apps/{app_id}/{account_id}
├── DELETE /moysklad/vendor/1.0/apps/{app_id}/{account_id}
└── PUT    /moysklad/vendor/1.0/apps/{app_id}/{account_id}/event

/api/hooks
├── GET    /subscriptions
├── POST   /subscriptions
├── PUT    /subscriptions/{id}
├── DELETE /subscriptions/{id}
└── POST   /webhook/{hook_id}

/api/customerorder
├── GET /search/for-payment
└── GET /{order_id}

/api/cashin
├── GET /search/for-payment
└── GET /{cashin_id}

/api/paymentin
└── GET /{payment_id}
```

## Запуск приложения

### Development
```bash
# Установка зависимостей
poetry install

# Настройка .env
cp .env.example .env
# Отредактировать .env

# Запуск
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Или через скрипт
poetry run python -m src.main
```

### Production
```bash
# С Gunicorn + Uvicorn workers
gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

## Конфигурация
```ini
# .env

# Database
APL_DATABASE_URL=sqlite+aiosqlite:///./db.sqlite3

# Server
APL_HOST=0.0.0.0
APL_PORT=8000

# МойСклад API
APL_MS_LOGIN=admin@your-company
APL_MS_PASSWORD=password123
APL_MS_BASE_URL=https://api.moysklad.ru/api/remap/1.2

# Webhooks
APL_MS_WEBHOOK_URL=https://your-domain.com/api/hooks/webhook
APL_WEBHOOK_TIMEOUT=30.0
APL_WEBHOOK_RETRY_ATTEMPTS=3

# Vendor API
APL_MS_APP_ID=your-app-id
APL_MS_APP_UID=your-app-uid
APL_MS_VENDOR_SECRET_KEY=your-secret-key

# Security
APL_ALLOWED_ORIGINS=["http://localhost:3000", "https://your-domain.com"]
APL_API_RATE_LIMIT=100

# Logging
APL_LOG_LEVEL=INFO
APL_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Порядок инициализации
```
1. Path("logs").mkdir(exist_ok=True)
   └─> Создание папки для логов

2. setup_logging()
   └─> Настройка logging с handlers

3. @asynccontextmanager lifespan
   └─> await init_db()
       └─> Создание таблиц
       └─> Применение manual migrations

4. FastAPI(lifespan=lifespan)
   └─> Создание app

5. app.add_middleware(CORSMiddleware)
   └─> Настройка CORS

6. if settings.api_rate_limit > 0:
   └─> Настройка rate limiting

7. for exc_class, handler in HANDLERS.items():
   └─> Регистрация exception handlers

8. app.mount("/static", ...)
   └─> Подключение static files

9. templates = Jinja2Templates(...)
   └─> Инициализация templates

10. app.include_router(...)
    └─> Регистрация всех роутеров

11. uvicorn.run(app)
    └─> Запуск сервера
```

## Особенности
```
╔═══════════════════════════════════════════════════════════════════╗
║                    КЛЮЧЕВЫЕ ОСОБЕННОСТИ                           ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. LIFESPAN MANAGEMENT                                           ║
║     • Правильное использование lifespan context manager           ║
║     • Инициализация БД при старте                                 ║
║     • Готовность для cleanup при остановке                        ║
║                                                                   ║
║  2. ЦЕНТРАЛИЗОВАННАЯ РЕГИСТРАЦИЯ                                  ║
║     • Все роутеры в одном месте                                   ║
║     • Все exception handlers в одном месте                        ║
║     • Единая точка входа                                          ║
║                                                                   ║
║  3. ОПЦИОНАЛЬНЫЙ RATE LIMITING                                    ║
║     • Включается через settings.api_rate_limit                    ║
║     • In-memory счетчики (не для production!)                     ║
║     • Per-IP ограничение                                          ║
║                                                                   ║
║  4. CORS ДЛЯ WEB UI                                               ║
║     • Настройка через allowed_origins                             ║
║     • Поддержка credentials                                       ║
║     • Все методы и headers разрешены                              ║
║                                                                   ║
║  5. STATIC FILES & TEMPLATES                                      ║
║     • Jinja2 для HTML rendering                                   ║
║     • StaticFiles для CSS/JS                                      ║
║     • Главная страница с UI                                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

## Примеры использования

### Добавление нового роутера
```python
# 1. Создать роутер в модуле
# src/apps/newmodule/api.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/example")
async def example():
    return {"message": "Hello"}

# 2. Импортировать в main.py
from src.apps.newmodule.api import router as newmodule_router

# 3. Зарегистрировать
app.include_router(
    newmodule_router,
    prefix="/api/newmodule",
    tags=["newmodule"]
)
```

### Добавление exception handlers
```python
# 1. Определить handlers в модуле
# src/apps/newmodule/exception_handlers.py
from fastapi.responses import JSONResponse

async def my_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)},
    )

EXCEPTION_HANDLERS = {
    MyException: my_exception_handler,
}

# 2. Импортировать в main.py
from src.apps.newmodule.exception_handlers import (
    EXCEPTION_HANDLERS as NEWMODULE_EXCEPTION_HANDLERS,
)

# 3. Зарегистрировать
for exc_class, handler in NEWMODULE_EXCEPTION_HANDLERS.items():
    app.add_exception_handler(exc_class, handler)
```

### Настройка дополнительного middleware
```python
# main.py
from fastapi import Request
import time

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование всех запросов."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logging.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    
    return response
```

## Связанные модули
```
┌─────────────────────────────────────────────────────────────────┐
│                    ИСПОЛЬЗУЕМЫЕ МОДУЛИ                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  core                                                           │
│    └─► config.settings                                          │
│    └─► database.init_db()                                       │
│    └─► logging_config.setup_logging()                           │
│                                                                 │
│  ms_auth                                                        │
│    └─► api.router (OAuth endpoints)                             │
│                                                                 │
│  vendor_api                                                     │
│    └─► api.router (Vendor API lifecycle)                        │
│                                                                 │
│  hooks                                                          │
│    └─► api.router (Webhook management)                          │
│    └─► exception_handlers.EXCEPTION_HANDLERS                    │
│                                                                 │
│  customerorder, cashin, paymentin                               │
│    └─► api.router (Document endpoints)                          │
│    └─► exception_handlers.EXCEPTION_HANDLERS                    │
│                                                                 │
│  static/, templates/                                            │
│    └─► Web UI files                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Healthcheck
```python
# Можно добавить healthcheck endpoint:
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(UTC).isoformat(),
    }

# Использование:
# curl http://localhost:8000/health
```

## Graceful Shutdown
```python
# Можно добавить cleanup в lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Application started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gracefully...")
    # Закрыть соединения с БД
    # Завершить фоновые задачи
    # Flush логи
    logger.info("Shutdown complete")
```