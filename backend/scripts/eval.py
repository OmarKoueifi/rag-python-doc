"""Golden retrieval suite. Exits non-zero on unknown regressions only.

Usage:
    python scripts/eval.py                 # run, print results
    python scripts/eval.py --write-md      # also regenerate EVAL_RESULTS.md
    python scripts/eval.py --top-k 10      # override top-k
    python scripts/eval.py --no-check      # report only, never exit non-zero
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from openai import OpenAI

from app.core.config import REPO_ROOT, get_settings
from app.rag.models import RetrievedChunk
from app.rag.retriever import Retriever

EVAL_MD_PATH = REPO_ROOT / "EVAL_RESULTS.md"
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class Expected:
    # Substring-matched against retrieved chunks' anchor metadata.
    # API anchors are dotted names ("asyncio.gather");
    # prose anchors are HTML fragment IDs ("user-defined-generic-types").
    anchor_substring: str
    max_rank: int
    description: str = ""
    required: bool = True


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    rationale: str
    expected: tuple[Expected, ...]
    known_issue: str | None = None


CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="q1_concurrent_coroutines",
        query="How do I run multiple coroutines concurrently?",
        rationale=(
            "Natural-language how-to. The canonical answers are asyncio.gather "
            "and (3.11+) asyncio.TaskGroup."
        ),
        expected=(
            Expected(
                anchor_substring="asyncio.gather",
                max_rank=5,
                description="Primary API for running awaitables concurrently",
            ),
            Expected(
                anchor_substring="asyncio.TaskGroup",
                max_rank=5,
                description="Structured-concurrency context manager (3.11+)",
                required=False,
            ),
        ),
        known_issue=(
            "Prose section chunks outrank terse API signatures on "
            "natural-language how-to queries. `asyncio.gather` does exist in "
            "the index and is retrievable at rank 1 when queried by its "
            "literal name — it just loses to conversational prose chunks on "
            "this phrasing."
        ),
    ),
    EvalCase(
        id="q2_optional_vs_union",
        query="What is the difference between Optional and Union in typing?",
        rationale="Comparison of two specific API entries; both should surface together.",
        expected=(
            Expected(anchor_substring="typing.Optional", max_rank=3),
            Expected(anchor_substring="typing.Union", max_rank=3),
        ),
    ),
    EvalCase(
        id="q3_generic_class",
        query="How do I make a generic class in Python?",
        rationale="Should retrieve the user-defined generics prose plus the Generic base class.",
        expected=(
            Expected(anchor_substring="typing.Generic", max_rank=5),
            Expected(
                anchor_substring="user-defined-generic-types",
                max_rank=5,
                description="Prose section on user-defined generics",
            ),
        ),
    ),
    EvalCase(
        id="q4_api_exact_name",
        query="asyncio.sleep",
        rationale="Literal API name lookup — must be rank 1.",
        expected=(
            Expected(anchor_substring="asyncio.sleep", max_rank=1),
        ),
    ),
    EvalCase(
        id="q5_protocol_ambiguous",
        query="What is a Protocol?",
        rationale=(
            "Ambiguous term: valid in both asyncio (transport protocols) and "
            "typing (structural subtyping via typing.Protocol). A well-tuned "
            "retriever surfaces both interpretations."
        ),
        expected=(
            Expected(
                anchor_substring="typing.Protocol",
                max_rank=5,
                description="typing.Protocol — structural subtyping",
            ),
            Expected(
                anchor_substring="asyncio.Protocol",
                max_rank=5,
                description="asyncio.Protocol — streaming transport protocol",
                required=False,
            ),
        ),
        known_issue=(
            "Module imbalance: the asyncio-protocol.html page contributes 8+ "
            "BaseProtocol/Protocol/DatagramProtocol/etc. entries, while typing "
            "contributes one `typing.Protocol` entry. Top-5 saturates with "
            "asyncio entries before `typing.Protocol` can appear. Cosine "
            "similarity alone has no mechanism to enforce module diversity."
        ),
    ),
)


Outcome = Literal["pass", "fail", "known_fail", "known_fail_now_passing"]


@dataclass
class Match:
    expected: Expected
    rank: int | None
    found_anchor: str | None

    @property
    def passed(self) -> bool:
        return self.rank is not None and self.rank <= self.expected.max_rank


@dataclass
class CaseResult:
    case: EvalCase
    retrieved: list[RetrievedChunk]
    matches: list[Match]

    @property
    def required_passed(self) -> bool:
        return all(m.passed for m in self.matches if m.expected.required)

    @property
    def outcome(self) -> Outcome:
        if self.case.known_issue is None:
            return "pass" if self.required_passed else "fail"
        return "known_fail_now_passing" if self.required_passed else "known_fail"


def run_case(retriever: Retriever, case: EvalCase, top_k: int) -> CaseResult:
    retrieved = retriever.retrieve(case.query, top_k=top_k)
    matches: list[Match] = []
    for exp in case.expected:
        found_rank: int | None = None
        found_anchor: str | None = None
        for rank, chunk in enumerate(retrieved, start=1):
            if exp.anchor_substring in chunk.anchor:
                found_rank = rank
                found_anchor = chunk.anchor
                break
        matches.append(Match(exp, found_rank, found_anchor))
    return CaseResult(case, retrieved, matches)


OUTCOME_LABEL: dict[Outcome, str] = {
    "pass": "PASS",
    "fail": "FAIL",
    "known_fail": "KNOWN FAIL",
    "known_fail_now_passing": "IMPROVED",
}


def print_terminal(results: list[CaseResult], top_k: int) -> None:
    print(f"\nRetrieval eval — top_k={top_k}")
    print("=" * 72)
    for r in results:
        label = OUTCOME_LABEL[r.outcome]
        print(f"  [{label:10s}] {r.case.id}")
        for m in r.matches:
            req = "required" if m.expected.required else "bonus   "
            if m.rank is not None:
                status = "✓" if m.passed else "✗"
                rank_s = f"rank {m.rank} (max {m.expected.max_rank})"
            else:
                status = "✗"
                rank_s = f"not in top-{top_k}"
            print(f"      {status} {req}  {m.expected.anchor_substring:40s} {rank_s}")
    print("=" * 72)
    counts: dict[Outcome, int] = {}
    for r in results:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1
    pieces = [f"{counts.get(o, 0)} {OUTCOME_LABEL[o].lower()}"
              for o in ("pass", "known_fail", "known_fail_now_passing", "fail")
              if counts.get(o)]
    print("  " + " · ".join(pieces))
    print()


def render_markdown(results: list[CaseResult], top_k: int, settings) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    counts: dict[Outcome, int] = {}
    for r in results:
        counts[r.outcome] = counts.get(r.outcome, 0) + 1

    lines: list[str] = [
        "# Retrieval Evaluation",
        "",
        "Auto-generated by `backend/scripts/eval.py`. Re-run with:",
        "",
        "```bash",
        "cd backend && python scripts/eval.py --write-md",
        "```",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run at | {now} |",
        f"| Collection | `{settings.chroma_collection}` |",
        f"| Embedding model | `{settings.openai_embedding_model}` |",
        f"| top_k | {top_k} |",
        f"| Cases | {len(results)} |",
        "",
        "## Summary",
        "",
        "| # | Case | Query | Outcome |",
        "|---|---|---|---|",
    ]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"| {i} | `{r.case.id}` | {_md_escape(r.case.query)} | **{OUTCOME_LABEL[r.outcome]}** |"
        )

    lines.extend(
        [
            "",
            "**"
            + " · ".join(
                f"{counts.get(o, 0)} {OUTCOME_LABEL[o].lower()}"
                for o in ("pass", "known_fail", "known_fail_now_passing", "fail")
                if counts.get(o)
            )
            + "**",
            "",
            "A KNOWN FAIL is a documented retrieval weakness we've chosen not to fix "
            "in the baseline — see each case's _Known issue_ note. If one flips to "
            "IMPROVED after a tuning change, update this file and treat it as progress.",
            "",
            "## Cases",
            "",
        ]
    )

    for i, r in enumerate(results, start=1):
        lines.extend(_render_case(i, r, top_k))

    return "\n".join(lines) + "\n"


def _render_case(i: int, r: CaseResult, top_k: int) -> list[str]:
    out: list[str] = [
        f"### {i}. `{r.case.id}` — {OUTCOME_LABEL[r.outcome]}",
        "",
        f"**Query:** {r.case.query}",
        "",
        f"_{r.case.rationale}_",
        "",
        "**Expected hits:**",
        "",
        "| Anchor | Max rank | Required | Found rank | Result |",
        "|---|---|---|---|---|",
    ]
    for m in r.matches:
        anchor = f"`{m.expected.anchor_substring}`"
        req = "yes" if m.expected.required else "bonus"
        if m.rank is None:
            found = "—"
            result = f"❌ not in top-{top_k}"
        elif m.passed:
            found = str(m.rank)
            result = "✅"
        else:
            found = str(m.rank)
            result = f"❌ exceeds max rank {m.expected.max_rank}"
        out.append(f"| {anchor} | {m.expected.max_rank} | {req} | {found} | {result} |")

    out.extend(["", "**Top-k retrieved:**", "", "| Rank | Sim | Kind | Module | Anchor / heading |", "|---|---|---|---|---|"])
    for rank, chunk in enumerate(r.retrieved, start=1):
        anchor = f"`{chunk.anchor}`" if chunk.anchor else "_(no anchor)_"
        out.append(
            f"| {rank} | {chunk.similarity:.3f} | {chunk.kind} | "
            f"{chunk.module} | {anchor} — {_md_escape(chunk.heading_path)} |"
        )

    if r.case.known_issue:
        out.extend(["", "**Known issue.** " + _md_escape_multiline(r.case.known_issue)])
    out.extend(["", "---", ""])
    return out


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def _md_escape_multiline(s: str) -> str:
    return " ".join(s.split())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    p.add_argument(
        "--write-md",
        action="store_true",
        help=f"Regenerate {EVAL_MD_PATH.relative_to(REPO_ROOT)} from current results.",
    )
    p.add_argument(
        "--no-check",
        action="store_true",
        help="Don't exit non-zero on unknown regressions; report only.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    openai_client = OpenAI(api_key=settings.openai_api_key)

    retriever = Retriever(
        chroma_path=settings.chroma_path_abs,
        collection_name=settings.chroma_collection,
        embed_model=settings.openai_embedding_model,
        openai_client=openai_client,
    )

    results: list[CaseResult] = []
    for case in CASES:
        results.append(run_case(retriever, case, args.top_k))

    print_terminal(results, args.top_k)

    if args.write_md:
        md = render_markdown(results, args.top_k, settings)
        EVAL_MD_PATH.write_text(md, encoding="utf-8")
        print(f"Wrote {EVAL_MD_PATH.relative_to(REPO_ROOT)}\n")

    unknown_fails = [r for r in results if r.outcome == "fail"]
    if unknown_fails and not args.no_check:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
