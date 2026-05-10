"""Insert the captured seed fixture into the admin database.

Reads data/seed_fixture.json (produced by scripts/capture_seed.py
runs the real chat pipeline once and snapshots actual answers + retrievals + flags).
Idempotent: skips when the DB already has rows; --reset wipes first.

Usage:
    python scripts/seed_db.py             # insert if tables are empty
    python scripts/seed_db.py --reset     # wipe then insert
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from sqlalchemy import delete, func, select

from app.core.config import BACKEND_ROOT
from app.db.models import FlaggedInput, Question, RetrievedSource
from app.db.session import _Session, create_all

FIXTURE_PATH = BACKEND_ROOT / "data" / "seed_fixture.json"


def _load_fixture() -> dict:
    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"{FIXTURE_PATH.relative_to(BACKEND_ROOT)} not found. "
            f"Run `python scripts/capture_seed.py` first."
        )
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


async def _is_empty() -> bool:
    async with _Session() as db:
        q = (await db.execute(select(func.count()).select_from(Question))).scalar_one()
        f = (await db.execute(select(func.count()).select_from(FlaggedInput))).scalar_one()
    return q == 0 and f == 0


async def _wipe() -> None:
    async with _Session() as db:
        await db.execute(delete(RetrievedSource))
        await db.execute(delete(Question))
        await db.execute(delete(FlaggedInput))
        await db.commit()


async def _seed() -> None:
    fixture = _load_fixture()
    now = datetime.now(UTC)

    async with _Session() as db:
        for q in fixture["questions"]:
            sources = q.get("sources", [])
            avg_sim = (
                sum(s["similarity"] for s in sources) / len(sources) if sources else None
            )
            row = Question(
                session_id=q["session_id"],
                question=q["question"],
                answer=q["answer"],
                moderation_blocked=q["moderation_blocked"],
                avg_similarity=avg_sim,
                retrieval_count=len(sources),
                created_at=now - timedelta(minutes=q["minutes_ago"]),
            )
            row.sources = [
                RetrievedSource(
                    rank=s["rank"],
                    source_url=s["source_url"],
                    heading_path=s["heading_path"],
                    module=s["module"],
                    anchor=s["anchor"],
                    similarity=s["similarity"],
                )
                for s in sources
            ]
            db.add(row)

        for f in fixture["flagged"]:
            db.add(
                FlaggedInput(
                    session_id=f["session_id"],
                    question=f["question"],
                    flag_type=f["flag_type"],
                    flag_detail=f["flag_detail"],
                    blocked=f["blocked"],
                    created_at=now - timedelta(minutes=f["minutes_ago"]),
                )
            )

        await db.commit()


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe existing rows first.")
    args = parser.parse_args()

    fixture = _load_fixture()
    await create_all()

    if args.reset:
        await _wipe()
        print("→ Wiped existing rows.")
    elif not await _is_empty():
        print("Tables already populated — pass --reset to overwrite.")
        return 0

    await _seed()
    print(
        f"✓ Seeded {len(fixture['questions'])} questions and "
        f"{len(fixture['flagged'])} flag events from "
        f"{FIXTURE_PATH.relative_to(BACKEND_ROOT)} (captured {fixture['captured_at']})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
