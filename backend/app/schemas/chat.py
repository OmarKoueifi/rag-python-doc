from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.constants import MAX_QUESTION_CHARS


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)


class SourceRef(BaseModel):
    rank: int
    source_url: str
    heading_path: str
    module: str
    anchor: str
    similarity: float
