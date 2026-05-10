"""Resize chunks from the parser.

API chunks pass through untouched. Prose chunks merge with consecutive
siblings in the same section while under target size, and split at
paragraph boundaries (never mid-fence) when over the max.
"""

from __future__ import annotations

from functools import lru_cache

import tiktoken

from app.core.constants import CHUNK_MAX_TOKENS, CHUNK_MIN_TOKENS, CHUNK_TARGET_TOKENS

from .models import Chunk


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text))


def resize_chunks(chunks: list[Chunk]) -> list[Chunk]:
    out: list[Chunk] = []
    buffer: list[Chunk] = []
    buffer_tokens = 0

    def flush() -> None:
        nonlocal buffer, buffer_tokens
        if not buffer:
            return
        out.append(buffer[0] if len(buffer) == 1 else _merge(buffer))
        buffer = []
        buffer_tokens = 0

    for c in chunks:
        if c.kind == "api":
            flush()
            out.append(c)
            continue

        tokens = count_tokens(c.content)

        if tokens > CHUNK_MAX_TOKENS:
            flush()
            out.extend(_split_prose(c))
            continue

        if (
            buffer
            and buffer[0].heading_path == c.heading_path
            and buffer[0].source_url == c.source_url
            and buffer_tokens + tokens <= CHUNK_TARGET_TOKENS
        ):
            buffer.append(c)
            buffer_tokens += tokens
            continue

        if tokens < CHUNK_MIN_TOKENS:
            flush()
            buffer = [c]
            buffer_tokens = tokens
        else:
            flush()
            out.append(c)

    flush()
    return out


def _merge(chunks: list[Chunk]) -> Chunk:
    first = chunks[0]
    return Chunk(
        content="\n\n".join(c.content for c in chunks),
        heading_path=first.heading_path,
        source_url=first.source_url,
        module=first.module,
        kind="prose",
        anchor=first.anchor,
    )


def _split_prose(chunk: Chunk) -> list[Chunk]:
    paragraphs = _split_paragraphs(chunk.content)
    out: list[Chunk] = []
    buf: list[str] = []
    buf_tokens = 0
    for p in paragraphs:
        p_tokens = count_tokens(p)
        if buf and buf_tokens + p_tokens > CHUNK_TARGET_TOKENS:
            out.append(_from_parts(chunk, buf))
            buf = [p]
            buf_tokens = p_tokens
        else:
            buf.append(p)
            buf_tokens += p_tokens
    if buf:
        out.append(_from_parts(chunk, buf))
    return out


def _from_parts(template: Chunk, parts: list[str]) -> Chunk:
    return Chunk(
        content="\n\n".join(parts),
        heading_path=template.heading_path,
        source_url=template.source_url,
        module=template.module,
        kind="prose",
        anchor=template.anchor,
    )


def _split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    current: list[str] = []
    in_fence = False

    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and not line.strip():
            if current:
                para = "\n".join(current).strip()
                if para:
                    paragraphs.append(para)
                current = []
        else:
            current.append(line)

    if current:
        para = "\n".join(current).strip()
        if para:
            paragraphs.append(para)
    return paragraphs
