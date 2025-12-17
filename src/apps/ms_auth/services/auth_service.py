import logging
from typing import Optional

from src.core.config import settings

from ..domain.entities import MySkladCredentials
from ..domain.value_objects import BasicAuthHeader
from ..schemas import MySkladCredentialsIn, MySkladCredentialsOut

logger = logging.getLogger(__name__)


class MySkladAuthService:
    """Сервис для управления аутентификацией в МойСклад."""
    
    def __init__(self) -> None:
        self._credentials: Optional[MySkladCredentials] = None
        self._access_token: Optional[str] = None
        self._base_url: Optional[str] = None
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Загрузить credentials из переменных окружения."""
        if self._credentials is not None:
            return
        
        login = settings.ms_login
        password = settings.ms_password
        base_url = settings.ms_base_url
        
        if login and password:
            logger.info("Загружены credentials МойСклад из ENV: login=%s", login)
            try:
                creds_in = MySkladCredentialsIn(
                    login=login,
                    password=password,
                    base_url=base_url,
                )
                self._credentials = MySkladCredentials(
                    login=creds_in.login,
                    password=creds_in.password,
                    base_url=creds_in.base_url,
                )
                self._base_url = str(creds_in.base_url)
            except Exception as exc:
                logger.error("Ошибка валидации credentials из ENV: %s", exc)
                self._credentials = None
        else:
            logger.warning(
                "Credentials МойСклад не найдены в ENV (APL_MS_LOGIN, APL_MS_PASSWORD)"
            )

    def set_credentials(self, creds: MySkladCredentialsIn) -> None:
        """Установить новые credentials."""
        logger.info("Установлены новые credentials: login=%s", creds.login)
        self._credentials = MySkladCredentials(
            login=creds.login,
            password=creds.password,
            base_url=creds.base_url,
        )
        self._base_url = str(creds.base_url)
        self._access_token = None

    def _ensure_loaded(self) -> None:
        """Убедиться что credentials загружены."""
        if self._credentials is None:
            self._load_from_env()

    def get_credentials(self) -> Optional[MySkladCredentialsOut]:
        """Получить credentials без пароля."""
        self._ensure_loaded()
        if self._credentials is None:
            return None
        
        return MySkladCredentialsOut(
            login=self._credentials.login,
            base_url=self._credentials.base_url,
            has_password=bool(self._credentials.password),
        )
    
    def get_raw_credentials(self) -> Optional[MySkladCredentials]:
        """Получить полные credentials (для внутреннего использования)."""
        self._ensure_loaded()
        return self._credentials
    
    def get_base_url(self) -> str:
        if self._base_url:
            return str(self._base_url).rstrip("/")

        self._ensure_loaded()
        if self._credentials:
            return str(self._credentials.base_url).rstrip("/")

        raise ValueError("Base URL is not configured")

    def set_access_token(self, token: str, *, base_url: str | None = None) -> None:
        """Установить access token для работы по OAuth/Vendor API."""

        self._access_token = token
        if base_url:
            self._base_url = base_url

    def clear_access_token(self) -> None:
        self._access_token = None
    
    def get_basic_auth_header(self) -> Optional[dict]:
        """Получить заголовок Authorization (Basic или Bearer)."""
        self._ensure_loaded()

        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}

        if self._credentials is None:
            return None
        
        auth_header = BasicAuthHeader(token=self._credentials.get_basic_auth_token())

        return auth_header.to_dict()


_auth_service = MySkladAuthService()


def get_ms_auth_service() -> MySkladAuthService:
    """Dependency для получения сервиса аутентификации."""
    return _auth_service