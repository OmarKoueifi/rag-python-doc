from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


FlagType = Literal["moderation", "injection"]


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderation_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    avg_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    sources: Mapped[list["RetrievedSource"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="RetrievedSource.rank",
    )


class RetrievedSource(Base):
    __tablename__ = "retrieved_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        index=True,
    )
    rank: Mapped[int] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(512))
    heading_path: Mapped[str] = mapped_column(Text)
    module: Mapped[str] = mapped_column(String(32), index=True)
    anchor: Mapped[str] = mapped_column(String(128))
    similarity: Mapped[float] = mapped_column(Float)

    question: Mapped[Question] = relationship(back_populates="sources")


class FlaggedInput(Base):
    __tablename__ = "flagged_inputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    flag_type: Mapped[str] = mapped_column(String(16), index=True)
    flag_detail: Mapped[str] = mapped_column(Text)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
