import hashlib
from dataclasses import dataclass
from typing import Literal

ChunkKind = Literal["api", "prose"]


@dataclass(slots=True)
class Chunk:
    content: str
    heading_path: list[str]
    source_url: str
    module: str
    kind: ChunkKind
    anchor: str

    @property
    def heading_breadcrumb(self) -> str:
        return " > ".join(self.heading_path)

    @property
    def embedding_text(self) -> str:
        # Prefixing the heading breadcrumb materially boosts retrieval on
        # terse queries like "gather".
        if not self.heading_path:
            return self.content
        return f"{self.heading_breadcrumb}\n\n{self.content}"

    def stable_id(self) -> str:
        h = hashlib.sha256(self.embedding_text.encode("utf-8")).hexdigest()[:12]
        return f"{self.source_url}::{h}"


@dataclass(slots=True)
class RetrievedChunk:
    content: str
    heading_path: str
    source_url: str
    module: str
    kind: str
    anchor: str
    similarity: float
