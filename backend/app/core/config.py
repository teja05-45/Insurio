"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "insecure-development-secret-change-before-deploying-0123456789"


class Settings(BaseSettings):
    """All runtime configuration. Values come from the environment or .env."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Insurio API"
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = DEFAULT_SECRET
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, ge=1, le=90)
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=240)

    # Database
    DATABASE_URL: str = "postgresql+psycopg://insurio:insurio@localhost:5432/insurio"
    DB_ECHO: bool = False

    # CORS: comma-separated origins.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Uploads
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_MB: int = Field(default=20, ge=1, le=100)
    MAX_PDF_PAGES: int = Field(default=400, ge=1, le=5000)
    OCR_ENABLED: bool = False

    # Retrieval / AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-20b"
    GROQ_TIMEOUT_SECONDS: int = Field(default=60, ge=5, le=300)
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=1.0)
    LLM_MAX_TOKENS: int = Field(default=1400, ge=256, le=8000)
    RETRIEVAL_TOP_K: int = Field(default=6, ge=1, le=12)
    RETRIEVAL_CANDIDATES: int = Field(default=24, ge=4, le=80)
    RETRIEVAL_MIN_SCORE: float = Field(default=0.0, ge=0.0, le=1.0)
    EMBEDDINGS_ENABLED: bool = True
    EMBEDDING_PROVIDER: Literal["auto", "fastembed", "sentence-transformers", "hashing", "none"] = (
        "auto"
    )
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSIONS: int = Field(default=384, ge=16, le=4096)
    INSIGHTS_LLM_ENRICHMENT: bool = True

    # Abuse control (per process; see docs/DECISIONS.md for Redis path)
    RATE_LIMIT_ENABLED: bool = True
    AUTH_RATE_LIMIT_PER_MINUTE: int = Field(default=20, ge=1, le=600)
    CHAT_RATE_LIMIT_PER_MINUTE: int = Field(default=30, ge=1, le=600)
    UPLOAD_RATE_LIMIT_PER_HOUR: int = Field(default=20, ge=1, le=600)

    # Usage display
    PLAN_QUESTION_QUOTA: int = 0  # 0 = unlimited

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def llm_configured(self) -> bool:
        return bool(self.GROQ_API_KEY.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
