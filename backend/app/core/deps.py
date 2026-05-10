from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI, OpenAI

from app.core.config import Settings, get_settings
from app.rag.retriever import Retriever

SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


@lru_cache
def _async_openai() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


@lru_cache
def _retriever() -> Retriever:
    s = get_settings()
    return Retriever(
        chroma_path=s.chroma_path_abs,
        collection_name=s.chroma_collection,
        embed_model=s.openai_embedding_model,
        openai_client=OpenAI(api_key=s.openai_api_key),
    )


def get_async_openai() -> AsyncOpenAI:
    return _async_openai()


def get_retriever() -> Retriever:
    return _retriever()


def get_settings_dep() -> Settings:
    return get_settings()
