from __future__ import annotations

from .models import RetrievedChunk

SYSTEM_PROMPT = """\
You are an assistant that answers questions about Python's standard library \
documentation, specifically the `asyncio` and `typing` modules. Use ONLY the \
provided documentation excerpts to answer. Cite sources by their bracketed \
number (e.g. [1], [2]) inline in your response. If the question is not about \
Python's asyncio or typing modules, politely decline and remind the user of \
your scope. If the provided excerpts do not contain the answer, say so \
honestly — do not guess, and do not fall back to outside knowledge.

Format answers in GitHub-flavored Markdown. When showing Python code, use \
triple-backtick ```python fences. Keep answers concise and grounded."""


REFUSAL_MODERATION = (
    "I can only help with questions about Python's `asyncio` and `typing` "
    "modules. Your message was flagged by content moderation and I'm not "
    "able to respond to it. Please rephrase and ask a documentation question."
)


def build_user_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    if not retrieved:
        return (
            f"Question: {question}\n\n"
            "No documentation excerpts were retrieved. Tell the user you don't "
            "have relevant documentation to answer this question."
        )

    lines: list[str] = ["Documentation excerpts:", ""]
    for i, r in enumerate(retrieved, start=1):
        lines.append(f"[{i}] {r.heading_path}")
        lines.append(f"Source: {r.source_url}")
        lines.append("")
        lines.append(r.content)
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(f"Question: {question}")
    lines.append("")
    lines.append(
        "Answer using only the excerpts above. Cite sources by their bracketed "
        "number. If the excerpts are insufficient, say so."
    )
    return "\n".join(lines)
