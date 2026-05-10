from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.deps import get_settings_dep
from app.db.models import FlaggedInput, Question, RetrievedSource
from app.db.session import get_db
from app.schemas.admin import (
    AuthStatus,
    DailyCount,
    FlaggedList,
    FlaggedRow,
    LoginRequest,
    Metrics,
    QuestionDetail,
    QuestionList,
    QuestionSummary,
    TopSource,
)
from app.schemas.chat import SourceRef
from app.security.admin_auth import (
    clear_cookie,
    issue_cookie,
    require_admin,
    verify_password,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=AuthStatus)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings_dep),
) -> AuthStatus:
    if not verify_password(body.password, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    issue_cookie(response, settings)
    return AuthStatus(authenticated=True)


@router.post("/logout", response_model=AuthStatus)
async def logout(
    response: Response,
    settings: Settings = Depends(get_settings_dep),
) -> AuthStatus:
    clear_cookie(response, settings)
    return AuthStatus(authenticated=False)


@router.get("/me", response_model=AuthStatus, dependencies=[Depends(require_admin)])
async def me() -> AuthStatus:
    return AuthStatus(authenticated=True)


@router.get(
    "/questions",
    response_model=QuestionList,
    dependencies=[Depends(require_admin)],
)
async def list_questions(
    db: Annotated[AsyncSession, Depends(get_db)],
    session_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    blocked: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QuestionList:
    filters = []
    if session_id:
        filters.append(Question.session_id == session_id)
    if date_from:
        filters.append(Question.created_at >= date_from)
    if date_to:
        filters.append(Question.created_at <= date_to)
    if blocked is not None:
        filters.append(Question.moderation_blocked.is_(blocked))

    total_stmt = select(func.count()).select_from(Question)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        select(Question)
        .order_by(desc(Question.created_at))
        .limit(limit)
        .offset(offset)
    )
    if filters:
        stmt = stmt.where(*filters)
    rows = (await db.execute(stmt)).scalars().all()

    return QuestionList(
        items=[QuestionSummary.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/questions/{question_id}",
    response_model=QuestionDetail,
    dependencies=[Depends(require_admin)],
)
async def question_detail(
    question_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionDetail:
    row = (
        await db.execute(
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.sources))
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return QuestionDetail(
        id=row.id,
        session_id=row.session_id,
        question=row.question,
        answer=row.answer,
        moderation_blocked=row.moderation_blocked,
        avg_similarity=row.avg_similarity,
        retrieval_count=row.retrieval_count,
        created_at=row.created_at,
        sources=[
            SourceRef(
                rank=s.rank,
                source_url=s.source_url,
                heading_path=s.heading_path,
                module=s.module,
                anchor=s.anchor,
                similarity=s.similarity,
            )
            for s in row.sources
        ],
    )


@router.get(
    "/metrics",
    response_model=Metrics,
    dependencies=[Depends(require_admin)],
)
async def metrics(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Metrics:
    total_questions = (
        await db.execute(select(func.count()).select_from(Question))
    ).scalar_one()
    total_blocked = (
        await db.execute(
            select(func.count()).select_from(Question).where(Question.moderation_blocked.is_(True))
        )
    ).scalar_one()
    total_flagged = (
        await db.execute(select(func.count()).select_from(FlaggedInput))
    ).scalar_one()

    mean_sim = (
        await db.execute(
            select(func.avg(Question.avg_similarity)).where(Question.avg_similarity.is_not(None))
        )
    ).scalar_one()

    since = datetime.now(UTC) - timedelta(days=14)
    day_expr = func.date(Question.created_at).label("day")
    daily_rows = (
        await db.execute(
            select(day_expr, func.count().label("count"))
            .where(Question.created_at >= since)
            .group_by(day_expr)
            .order_by(day_expr)
        )
    ).all()

    top_rows = (
        await db.execute(
            select(
                RetrievedSource.source_url,
                RetrievedSource.heading_path,
                RetrievedSource.module,
                func.count().label("count"),
            )
            .group_by(
                RetrievedSource.source_url,
                RetrievedSource.heading_path,
                RetrievedSource.module,
            )
            .order_by(desc("count"))
            .limit(10)
        )
    ).all()

    return Metrics(
        total_questions=total_questions,
        total_blocked=total_blocked,
        total_flagged=total_flagged,
        mean_similarity=float(mean_sim) if mean_sim is not None else None,
        questions_per_day=[
            DailyCount(day=str(r.day), count=int(r.count)) for r in daily_rows
        ],
        top_sources=[
            TopSource(
                source_url=r.source_url,
                heading_path=r.heading_path,
                module=r.module,
                count=int(r.count),
            )
            for r in top_rows
        ],
    )


@router.get(
    "/flagged",
    response_model=FlaggedList,
    dependencies=[Depends(require_admin)],
)
async def list_flagged(
    db: Annotated[AsyncSession, Depends(get_db)],
    flag_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FlaggedList:
    filters = []
    if flag_type:
        filters.append(FlaggedInput.flag_type == flag_type)

    total_stmt = select(func.count()).select_from(FlaggedInput)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        select(FlaggedInput)
        .order_by(desc(FlaggedInput.created_at))
        .limit(limit)
        .offset(offset)
    )
    if filters:
        stmt = stmt.where(*filters)
    rows = (await db.execute(stmt)).scalars().all()

    return FlaggedList(
        items=[FlaggedRow.model_validate(r) for r in rows],
        total=total,
    )
