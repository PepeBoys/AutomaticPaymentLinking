from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"

    # Container
    host: str = "0.0.0.0"
    port: int = 8000
    
    # МойСклад API
    ms_login: str = ""
    ms_password: str = ""
    ms_base_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    # Webhooks
    ms_webhook_url: str = ""
    webhook_timeout: float = 30.0
    webhook_retry_attempts: int = 3
    webhook_request_ttl_seconds: int = 3600

    # Security
    allowed_origins: list[str] = ["http://localhost:3000", "https://your-domain.com"]
    api_rate_limit: int = 100

    # МойСклад Vendor API
    ms_app_id: str = ""
    ms_app_uid: str = ""
    ms_vendor_secret_key: str = ""
    vendor_api_endpoint_base: str = ""
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APL_",
        extra="ignore",
        env_file_encoding="utf-8",
    )


settings = Settings()
