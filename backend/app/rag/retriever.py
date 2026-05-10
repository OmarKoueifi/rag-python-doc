from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI

from .models import RetrievedChunk


class Retriever:
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
        self._collection = self._client.get_collection(name=collection_name)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        emb = (
            self._openai.embeddings.create(model=self._embed_model, input=[query])
            .data[0]
            .embedding
        )
        res = self._collection.query(
            query_embeddings=[emb],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents: list[str] = res["documents"][0]
        metadatas: list[dict[str, str]] = res["metadatas"][0]
        distances: list[float] = res["distances"][0]
        return [
            RetrievedChunk(
                content=doc,
                heading_path=meta["heading_path"],
                source_url=meta["source_url"],
                module=meta["module"],
                kind=meta["kind"],
                anchor=meta["anchor"],
                similarity=1.0 - float(dist),
            )
            for doc, meta, dist in zip(documents, metadatas, distances, strict=True)
        ]
