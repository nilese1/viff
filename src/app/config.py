from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    development = "development"
    test = "test"
    production = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.development
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    secret_key: str = "dev-secret-change-me"

    database_url: str | None = None
    sqlite_path: str = "./data/dev.db"

    url_polling_rate_secs: int = 60

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnv.production

    @property
    def resolved_database_url(self) -> str:
        if self.is_production:
            if not self.database_url:
                raise RuntimeError("DATABASE_URL must be set when APP_ENV=production")
            return self.database_url
        if self.app_env is AppEnv.test:
            return "sqlite+aiosqlite:///:memory:"
        return f"sqlite+aiosqlite:///{self.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
