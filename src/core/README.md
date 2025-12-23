# Core - Инфраструктурные компоненты приложения

## Описание

Модуль `core` содержит базовые инфраструктурные компоненты приложения, которые используются во всех остальных модулях. Это фундамент приложения, обеспечивающий конфигурацию, работу с БД, логирование и базовые паттерны.

**Ключевое назначение**: Предоставить единообразную инфраструктуру для всех модулей приложения через переиспользуемые компоненты и паттерны.

## Архитектура
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORE INFRASTRUCTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  config.py - Конфигурация приложения                               │     │
│  │  • Settings (Pydantic BaseSettings)                                │     │
│  │  • Загрузка из .env файла                                          │     │
│  │  • Типизированные настройки                                        │     │
│  │  • Валидация через Pydantic                                        │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  database.py - Управление БД                                       │     │
│  │  • DatabaseManager - менеджер подключений                          │     │
│  │  • get_session() - FastAPI dependency                              │     │
│  │  • init_db() - инициализация БД                                    │     │
│  │  • Manual migrations - ручные миграции                             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  models.py - Базовая модель SQLAlchemy                             │     │
│  │  • Base (DeclarativeBase)                                          │     │
│  │  • id, created_at, updated_at, is_active                           │     │
│  │  • Автоматическое именование таблиц                                │     │
│  │  • Soft delete support                                             │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  repository.py - Базовый репозиторий                               │     │
│  │  • SQLAlchemyRepository<T> (Generic)                               │     │
│  │  • CRUD операции                                                   │     │
│  │  • Soft/Hard delete                                                │     │
│  │  • Filter support                                                  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  uow.py - Unit of Work интерфейс                                   │     │
│  │  • IUnitOfWork (ABC)                                               │     │
│  │  • commit/rollback abstraction                                     │     │
│  │  • Context manager protocol                                        │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  logging_config.py - Настройка логирования                         │     │
│  │  • setup_logging()                                                 │     │
│  │  • File + Console handlers                                         │     │
│  │  • Configurable log level                                          │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Компоненты

### 1. Settings (config.py)
```python
class Settings(BaseSettings):
    """Централизованная конфигурация приложения."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"
    
    # МойСклад API
    ms_login: str = ""
    ms_password: str = ""
    ms_base_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    # Webhooks
    ms_webhook_url: str = ""
    webhook_timeout: float = 30.0
    webhook_retry_attempts: int = 3
    
    # МойСклад Vendor API
    ms_app_id: str = ""
    ms_app_uid: str = ""
    ms_vendor_secret_key: str = ""
    
    # Security
    allowed_origins: list[str] = [...]
    api_rate_limit: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "..."
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APL_",  # Automatic Payment Linking
        extra="ignore",
    )

# Использование:
from src.core.config import settings

base_url = settings.ms_base_url
timeout = settings.webhook_timeout
```

**Особенности**:
- Загрузка из `.env` с префиксом `APL_`
- Типизация и валидация через Pydantic
- Значения по умолчанию
- Единственная точка конфигурации

### 2. DatabaseManager (database.py)
```python
class DatabaseManager:
    """Менеджер для управления подключением к БД и сессиями."""
    
    def __init__(self, url: str, echo: bool = False):
        self.engine = create_async_engine(url, echo=echo)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    
    def get_scope_session(self) -> async_scoped_session:
        """Scoped сессия для текущей задачи."""
        return async_scoped_session(
            session_factory=self.session_factory,
            scopefunc=current_task,
        )
    
    async def session_dependency(self):
        """Обычная сессия для FastAPI."""
        async with self.session_factory() as session:
            yield session

# Использование:
from src.core.database import get_session

@router.get("/example")
async def example(session: AsyncSession = Depends(get_session)):
    # Работа с БД
    pass
```

**Особенности**:
- Async engine и sessions
- FastAPI dependency для сессий
- Scoped sessions для изоляции задач
- Auto-close сессий

### 3. Base Model (models.py)
```python
class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    
    __abstract__ = True
    
    # Автоматическое именование таблиц
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{cls.__name__.lower()}s"
    
    # Стандартные поля для всех моделей
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

# Использование:
from src.core.models import Base

class WebhookSubscription(Base):
    # Автоматически: __tablename__ = "webhooksubscriptions"
    # Автоматически: id, created_at, updated_at, is_active
    
    account_id: Mapped[str] = mapped_column(String(128))
    # ... остальные поля
```

**Особенности**:
- Автоматическое именование таблиц (ClassName → classnames)
- Стандартные поля: id, timestamps, soft delete
- Индексы на id и is_active
- Timezone-aware timestamps

### 4. SQLAlchemyRepository (repository.py)
```python
class SQLAlchemyRepository(ABC, Generic[T]):
    """Базовый репозиторий для работы с SQLAlchemy."""
    
    model: Type[T] = None
    
    async def create(self, **data) -> T:
        """Создать объект."""
        
    async def get_all(self, order_by=None) -> List[T]:
        """Получить все активные объекты."""
        
    async def get_by_id(self, obj_id: str) -> Optional[T]:
        """Получить объект по ID."""
        
    async def get_one(self, **filter_by) -> Optional[T]:
        """Получить один объект по фильтру."""
        
    async def update(self, obj_id: str, **data) -> Optional[T]:
        """Обновить объект."""
        
    async def soft_delete(self, obj_id: str) -> None:
        """Мягкое удаление (is_active=False)."""
        
    async def hard_delete(self, **filter_by) -> None:
        """Жесткое удаление из БД."""

# Использование:
class WebhookRepository(SQLAlchemyRepository[WebhookSubscription]):
    model = WebhookSubscription
    
    # Автоматически все CRUD методы
    # Можно добавить специфичные методы
```

**Особенности**:
- Generic типизация
- Автоматическая фильтрация по is_active
- Soft delete по умолчанию
- Можно расширять специфичными методами

### 5. IUnitOfWork (uow.py)
```python
class IUnitOfWork(ABC):
    """Интерфейс Unit of Work."""
    
    async def __aenter__(self):
        """Начало транзакции."""
        
    async def __aexit__(self, *args):
        """Завершение транзакции."""
        
    async def commit(self) -> None:
        """Зафиксировать изменения."""
        
    async def rollback(self) -> None:
        """Откатить изменения."""

# Использование:
class UnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session
        self.webhooks = WebhookRepository(session)
        # ... другие репозитории
    
    async def commit(self):
        await self._session.commit()
    
    async def rollback(self):
        await self._session.rollback()

# В сервисах:
async with uow:
    await uow.webhooks.create(...)
    await uow.commit()
```

**Особенности**:
- Context manager protocol
- Управление транзакциями
- Группировка репозиториев
- Atomic операции

### 6. Logging Setup (logging_config.py)
```python
def setup_logging() -> None:
    """Настройка логирования для всего приложения."""
    
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format=settings.log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),  # Console
            logging.FileHandler("logs/app.log"),  # File
        ],
    )
    
    # Отключение шумных библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

# Использование в main.py:
from src.core.logging_config import setup_logging

setup_logging()
```

**Особенности**:
- Двойной вывод (console + file)
- Конфигурируемый уровень
- Автоматическое создание папки logs
- Фильтрация шумных библиотек

## Manual Migrations
```python
def _apply_manual_migrations(sync_conn) -> None:
    """Простые ручные миграции для поддержания схемы."""
    
    inspector = inspect(sync_conn)
    
    # Проверка существования таблицы
    if "webhooksubscriptions" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("webhooksubscriptions")}
        
        # Добавление нового столбца
        if "payment_purpose_mask" not in columns:
            sync_conn.exec_driver_sql(
                "ALTER TABLE webhooksubscriptions "
                "ADD COLUMN payment_purpose_mask VARCHAR(512)"
            )
        
        # Добавление индекса
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("webhooksubscriptions")}
        if "ix_webhook_account_payment" not in existing_indexes:
            sync_conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_webhook_account_payment "
                "ON webhooksubscriptions (ms_account_id, payment_type)"
            )
```

**Особенности**:
- Проверка существования перед добавлением
- Работает при init_db()
- Простые миграции без Alembic
- Поддержка обновления схемы

## Примеры использования

### Полный пример с всеми компонентами
```python
# 1. Конфигурация
from src.core.config import settings

base_url = settings.ms_base_url
timeout = settings.webhook_timeout

# 2. Модель
from src.core.models import Base

class MyModel(Base):
    # Автоматически: __tablename__ = "mymodels"
    # Автоматически: id, created_at, updated_at, is_active
    name: Mapped[str] = mapped_column(String(255))

# 3. Репозиторий
from src.core.repository import SQLAlchemyRepository

class MyRepository(SQLAlchemyRepository[MyModel]):
    model = MyModel
    
    async def get_by_name(self, name: str) -> MyModel | None:
        return await self.get_one(name=name)

# 4. Unit of Work
from src.core.uow import IUnitOfWork

class MyUnitOfWork(IUnitOfWork):
    def __init__(self, session: AsyncSession):
        self._session = session
        self.my_models = MyRepository(session)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.rollback()
    
    async def commit(self):
        await self._session.commit()
    
    async def rollback(self):
        await self._session.rollback()

# 5. Использование в API
from src.core.database import get_session

@router.post("/my-endpoint")
async def create_my_model(
    name: str,
    session: AsyncSession = Depends(get_session),
):
    uow = MyUnitOfWork(session)
    
    async with uow:
        model = await uow.my_models.create(name=name)
        await uow.commit()
    
    return {"id": model.id, "name": model.name}
```

## Используется в
```
┌─────────────────────────────────────────────────────────────────┐
│                 ВСЕ МОДУЛИ ИСПОЛЬЗУЮТ CORE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ms_auth                                                        │
│    └─► config.settings (ms_login, ms_password)                  │
│                                                                 │
│  hooks                                                          │
│    └─► models.Base                                              │
│    └─► repository.SQLAlchemyRepository                          │
│    └─► uow.IUnitOfWork                                          │
│    └─► database.get_session                                     │
│                                                                 │
│  vendor_api                                                     │
│    └─► models.Base                                              │
│    └─► config.settings (vendor keys)                            │
│    └─► database.get_session                                     │
│                                                                 │
│  Все payment/document модули                                    │
│    └─► config.settings (webhook_timeout, retry_attempts)        │
│                                                                 │
│  main.py                                                        │
│    └─► logging_config.setup_logging()                           │
│    └─► database.init_db()                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Паттерны

### Repository Pattern
```
┌────────────────────────────────────────────────────────────┐
│              REPOSITORY PATTERN                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Преимущества:                                             │
│  • Абстракция над БД                                       │
│  • Переиспользование CRUD операций                         │
│  • Единообразный интерфейс                                 │
│  • Легко тестировать (mock repository)                     │
│  • Separation of concerns                                  │
│                                                            │
│  Недостатки:                                               │
│  • Дополнительный слой абстракции                          │
│  • Не все операции укладываются в generic методы           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Unit of Work Pattern
```
┌────────────────────────────────────────────────────────────┐
│            UNIT OF WORK PATTERN                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Преимущества:                                             │
│  • Группировка операций в транзакцию                       │
│  • Atomic commit/rollback                                  │
│  • Централизованное управление репозиториями               │
│  • Context manager для безопасности                        │
│                                                            │
│  Использование:                                            │
│  async with uow:                                           │
│      await uow.repo1.create(...)                           │
│      await uow.repo2.update(...)                           │
│      await uow.commit()  # All or nothing                  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Архитектурные решения

```
╔═══════════════════════════════════════════════════════════════════╗
║                  КЛЮЧЕВЫЕ РЕШЕНИЯ                                 ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  1. PYDANTIC SETTINGS                                             ║
║     • Типизация + валидация конфигурации                          ║
║     • Автоматическая загрузка из .env                             ║
║     • Централизованная конфигурация                               ║
║                                                                   ║
║  2. ASYNC SQLALCHEMY                                              ║
║     • Полностью асинхронный доступ к БД                           ║
║     • Scoped sessions для изоляции                                ║
║     • FastAPI dependency injection                                ║
║                                                                   ║
║  3. GENERIC REPOSITORY                                            ║
║     • Переиспользование CRUD операций                             ║
║     • Type safety через Generic[T]                                ║
║     • Расширяемость специфичными методами                         ║
║                                                                   ║
║  4. BASE MODEL С SOFT DELETE                                      ║
║     • Все модели имеют is_active                                  ║
║     • Безопасное удаление без потери данных                       ║
║     • Автоматическая фильтрация в репозитории                     ║
║                                                                   ║
║  5. MANUAL MIGRATIONS                                             ║
║     • Без Alembic для простоты                                    ║
║     • Проверка + добавление при init_db()                         ║
║     • Достаточно для небольших изменений схемы                    ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```