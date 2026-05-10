"""POST /api/chat — RAG endpoint with SSE streaming.

SSE event shapes (one JSON doc per ``data:`` line):
    {"type": "token",   "text": "hello "}
    {"type": "sources", "sources": [SourceRef, …]}
    {"type": "refusal", "message": "…"}
    {"type": "error",   "message": "…"}
    {"type": "done"}
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.deps import (
    SESSION_COOKIE_MAX_AGE_SECONDS,
    SESSION_COOKIE_NAME,
    get_async_openai,
    get_retriever,
    get_settings_dep,
)
from app.core.rate_limit import CHAT_LIMIT, limiter
from app.db.models import FlaggedInput, Question, RetrievedSource
from app.db.session import get_db
from app.rag.models import RetrievedChunk
from app.rag.prompts import REFUSAL_MODERATION, SYSTEM_PROMPT, build_user_prompt
from app.rag.retriever import Retriever
from app.schemas.chat import ChatRequest
from app.security import injection
from app.security.moderation import moderate

router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/chat",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
@limiter.limit(CHAT_LIMIT)
async def chat(
    request: Request,
    body: Annotated[ChatRequest, Body()],
    db: Annotated[AsyncSession, Depends(get_db)],
    retriever: Annotated[Retriever, Depends(get_retriever)],
    openai_client: Annotated[AsyncOpenAI, Depends(get_async_openai)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
):
    existing_sid = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = existing_sid or str(uuid.uuid4())

    resp = StreamingResponse(
        _event_stream(
            question=body.question,
            session_id=session_id,
            db=db,
            retriever=retriever,
            openai_client=openai_client,
            settings=settings,
        ),
        media_type="text/event-stream",
        headers={
            # Stop nginx/proxy buffering so tokens reach the client live.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
    if not existing_sid:
        resp.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=SESSION_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            path="/",
        )
    return resp


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


async def _event_stream(
    *,
    question: str,
    session_id: str,
    db: AsyncSession,
    retriever: Retriever,
    openai_client: AsyncOpenAI,
    settings: Settings,
) -> AsyncIterator[bytes]:
    try:
        moderation = await moderate(openai_client, question)
        if moderation.flagged:
            await _log_flagged(
                db,
                session_id=session_id,
                question=question,
                flag_type="moderation",
                detail=moderation.detail or "(no category)",
                blocked=True,
            )
            await _log_question(
                db,
                session_id=session_id,
                question=question,
                answer=None,
                moderation_blocked=True,
                retrieved=[],
            )
            yield _sse({"type": "refusal", "message": REFUSAL_MODERATION})
            yield _sse({"type": "done"})
            return

        matches = injection.detect(question)
        if matches:
            await _log_flagged(
                db,
                session_id=session_id,
                question=question,
                flag_type="injection",
                detail="; ".join(m.pattern_name for m in matches),
                blocked=False,
            )

        retrieved: list[RetrievedChunk] = await run_in_threadpool(
            retriever.retrieve, question, top_k=5
        )

        full_text_parts: list[str] = []
        stream = await openai_client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question, retrieved)},
            ],
            temperature=0.1,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text_parts.append(delta)
                yield _sse({"type": "token", "text": delta})

        # Persist before sending the closing events — if the client cancels
        # at the last second, the dashboard record is still safe.
        await _log_question(
            db,
            session_id=session_id,
            question=question,
            answer="".join(full_text_parts),
            moderation_blocked=False,
            retrieved=retrieved,
        )

        yield _sse(
            {
                "type": "sources",
                "sources": [
                    {
                        "rank": i,
                        "source_url": r.source_url,
                        "heading_path": r.heading_path,
                        "module": r.module,
                        "anchor": r.anchor,
                        "similarity": round(r.similarity, 4),
                    }
                    for i, r in enumerate(retrieved, start=1)
                ],
            }
        )
        yield _sse({"type": "done"})

    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        yield _sse({"type": "done"})


async def _log_question(
    db: AsyncSession,
    *,
    session_id: str,
    question: str,
    answer: str | None,
    moderation_blocked: bool,
    retrieved: list[RetrievedChunk],
) -> None:
    avg = sum(r.similarity for r in retrieved) / len(retrieved) if retrieved else None
    row = Question(
        session_id=session_id,
        question=question,
        answer=answer,
        moderation_blocked=moderation_blocked,
        avg_similarity=avg,
        retrieval_count=len(retrieved),
    )
    row.sources = [
        RetrievedSource(
            rank=i,
            source_url=r.source_url,
            heading_path=r.heading_path,
            module=r.module,
            anchor=r.anchor,
            similarity=r.similarity,
        )
        for i, r in enumerate(retrieved, start=1)
    ]
    db.add(row)
    await db.commit()


async def _log_flagged(
    db: AsyncSession,
    *,
    session_id: str,
    question: str,
    flag_type: str,
    detail: str,
    blocked: bool,
) -> None:
    db.add(
        FlaggedInput(
            session_id=session_id,
            question=question,
            flag_type=flag_type,
            flag_detail=detail,
            blocked=blocked,
        )
    )
    await db.commit()
