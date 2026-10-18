from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, SecretStr
from functools import lru_cache


class _Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


class DatabaseSettings(_Base):
    DATABASE_URL: str
    DEBUG: bool = False


class RedisSettings(_Base):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


class JWTSettings(_Base):
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


class ElasticsearchSettings(_Base):
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200


class EmailSettings(_Base):
    GMAIL_ADDRESS: EmailStr | None = None
    GMAIL_APP_PASSWORD: SecretStr | None = None


class Settings(
        DatabaseSettings,
        RedisSettings,
        JWTSettings,
        ElasticsearchSettings,
        EmailSettings):
    PROJECT_NAME: str = "Bookmark Manager"
    API_V1_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore


settings = get_settings()
