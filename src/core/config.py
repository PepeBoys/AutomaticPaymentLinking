from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./db.sqlite3"
    
    # МойСклад API
    ms_login: str = ""
    ms_password: str = ""
    ms_base_url: str = "https://api.moysklad.ru/api/remap/1.2"
    
    # Webhooks
    ms_webhook_url: str = ""

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