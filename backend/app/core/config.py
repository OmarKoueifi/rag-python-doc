from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(...)
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    admin_password: str = ""
    session_secret: str = ""

    environment: Literal["development", "production"] = "development"
    cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"
    chroma_collection: str = "python_docs"

    python_docs_version: str = "3.12.7"
    python_docs_modules: str = "asyncio,typing"

    chat_rate_limit_per_minute: int = 30

    seed_on_startup: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def modules_list(self) -> list[str]:
        return [m.strip() for m in self.python_docs_modules.split(",") if m.strip()]

    @property
    def chroma_path_abs(self) -> Path:
        p = Path(self.chroma_path)
        return p if p.is_absolute() else (BACKEND_ROOT / p).resolve()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
