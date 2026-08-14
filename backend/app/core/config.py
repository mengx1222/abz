from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# 使用 AZB_ 前缀避免与宿主项目环境变量冲突
ENV_PREFIX = "AZB_"


class Settings(BaseSettings):
    """应用配置，所有字段从环境变量或 .env 文件读取。

    环境变量使用 AZB_ 前缀，如 AZB_DATABASE_URL、AZB_DEMO_MODE 等。
    .env 文件中也应使用相同前缀。
    """

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "安诊保 AI 副驾"
    APP_VERSION: str = "1.0.0-rc.1"
    APP_ENV: str = "development"
    DEBUG: bool = True
    DEMO_MODE: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/anzhenbao"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT ---
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120
    REFRESH_EXPIRE_DAYS: int = 7

    # --- AI Provider ---
    AI_PROVIDER: str = "mock"  # mock / deepseek / qwen / openai
    AI_API_KEY: str = ""
    AI_BASE_URL: str = ""
    AI_MODEL: str = ""
    AI_EMBEDDING_MODEL: str = ""
    AI_RERANK_MODEL: str = ""

    # --- RAG Pipeline ---
    RAG_CHUNK_TARGET_TOKENS: int = 512
    RAG_CHUNK_OVERLAP_TOKENS: int = 50
    RAG_VECTOR_TOP_K: int = 20
    RAG_BM25_TOP_K: int = 20
    RAG_RERANK_TOP_K: int = 8
    RAG_RRF_K: int = 60
    RAG_MIN_RELEVANCE: float = 0.3
    RAG_MAX_CONTEXT_CHARS: int = 4000

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def effective_ai_provider(self) -> str:
        """有效AI Provider：Demo模式下强制使用mock。"""
        if self.DEMO_MODE:
            return "mock"
        return self.AI_PROVIDER


settings = Settings()
