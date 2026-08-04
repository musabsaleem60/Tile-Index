from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Tile Index API"
    app_env: str = "development"
    app_version: str = "1.0.0"
    secret_key: str
    access_token_expire_minutes: int = 480
    database_url: str
    backend_cors_origins: str = ""
    latest_desktop_version: str = "1.0.0"
    latest_desktop_download_url: str = ""
    latest_desktop_release_notes: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        if not self.backend_cors_origins.strip():
            return []
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
