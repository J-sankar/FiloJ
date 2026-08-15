# gateway/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    FILE_SERVICE_URL: str = "http://localhost:8002"
    AUTH_SERVICE_URL: str = "http://localhost:8001"

    FILE_SERVICE_TIMEOUT: float = 60.0
    AUTH_SERVICE_TIMEOUT: float = 10.0
    DEFAULT_TIMEOUT: float = 30.0

    INTERNAL_GATEWAY_SECRET: str | None = None
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def services(self) -> dict[str, str]:
        return {
            "file": self.FILE_SERVICE_URL,
            "auth": self.AUTH_SERVICE_URL,
        }

    @property
    def timeouts(self) -> dict[str, float]:
        return {
            "file": self.FILE_SERVICE_TIMEOUT,
            "auth": self.AUTH_SERVICE_TIMEOUT,
            "default": self.DEFAULT_TIMEOUT,
        }


settings = Settings()
