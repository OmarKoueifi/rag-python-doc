from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from .models import Chunk

EMBED_BATCH_SIZE = 100


class Indexer:
    def __init__(
        self,
        *,
        chroma_path: Path,
        collection_name: str,
        embed_model: str,
        openai_client: OpenAI,
    ) -> None:
        self._embed_model = embed_model
        self._openai = openai_client
        self._client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection_name = collection_name
        self._collection = self._get_or_create()

    def _get_or_create(self) -> Collection:
        return self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            pass
        self._collection = self._get_or_create()

    def count(self) -> int:
        return self._collection.count()

    def index(
        self,
        chunks: list[Chunk],
        *,
        on_batch: Callable[[int, int], None] | None = None,
    ) -> int:
        total = len(chunks)
        indexed = 0
        for batch in _batched(chunks, EMBED_BATCH_SIZE):
            resp = self._openai.embeddings.create(
                model=self._embed_model,
                input=[c.embedding_text for c in batch],
            )
            ids: list[str] = []
            embeddings: list[list[float]] = []
            documents: list[str] = []
            metadatas: list[dict[str, str]] = []
            for c, emb in zip(batch, resp.data, strict=True):
                ids.append(c.stable_id())
                embeddings.append(emb.embedding)
                documents.append(c.content)
                metadatas.append(
                    {
                        "heading_path": " > ".join(c.heading_path),
                        "source_url": c.source_url,
                        "module": c.module,
                        "kind": c.kind,
                        "anchor": c.anchor,
                    }
                )
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            indexed += len(ids)
            if on_batch is not None:
                on_batch(indexed, total)
        return indexed


def _batched(items: list[Chunk], size: int) -> Iterator[list[Chunk]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
