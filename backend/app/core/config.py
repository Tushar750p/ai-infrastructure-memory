from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Infrastructure Memory"
    database_url: str = Field(default="postgresql+psycopg2://postgres:postgres@localhost:5432/infra_memory")
    database_host: str | None = None
    database_user: str | None = None
    database_password: str | None = None
    database_name: str | None = None
    database_port: int = 5432
    redis_url: str = "redis://localhost:6379/0"
    credentials_encryption_key: str
    aws_session_duration_seconds: int = 900
    cors_allowed_origins: str = "http://localhost:3000"
    auth_cookie_secure: bool = False
    auth_cookie_name: str = "aime_session"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "AIME <no-reply@example.com>"
    smtp_use_tls: bool = True
    password_reset_url: str | None = None
    email_verification_url: str | None = None

    @model_validator(mode="after")
    def build_database_url(self):
        if all(v is not None for v in (
            self.database_host, self.database_user, self.database_password, self.database_name
        )):
            self.database_url = (
                f"postgresql+psycopg2://{quote_plus(self.database_user)}:"
                f"{quote_plus(self.database_password)}@{self.database_host}:"
                f"{self.database_port}/{self.database_name}"
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
