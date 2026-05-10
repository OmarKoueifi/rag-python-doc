from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .chat import SourceRef


class LoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=256)


class AuthStatus(BaseModel):
    authenticated: bool


class QuestionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    question: str
    answer: str | None
    moderation_blocked: bool
    avg_similarity: float | None
    retrieval_count: int
    created_at: datetime


class QuestionDetail(QuestionSummary):
    sources: list[SourceRef]


class QuestionList(BaseModel):
    items: list[QuestionSummary]
    total: int
    limit: int
    offset: int


class DailyCount(BaseModel):
    day: str
    count: int


class TopSource(BaseModel):
    source_url: str
    heading_path: str
    module: str
    count: int


class Metrics(BaseModel):
    total_questions: int
    total_blocked: int
    total_flagged: int
    mean_similarity: float | None
    questions_per_day: list[DailyCount]
    top_sources: list[TopSource]


class FlaggedRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    question: str
    flag_type: str
    flag_detail: str
    blocked: bool
    created_at: datetime


class FlaggedList(BaseModel):
    items: list[FlaggedRow]
    total: int
