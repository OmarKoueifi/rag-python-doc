"""Parse Python docs HTML into Chunks.

The docs use a predictable Sphinx structure: nested ``<section>`` for the
heading hierarchy, and ``<dl class="py function|class|method|...">`` for
each individual API entry. Each ``<dl>`` becomes its own chunk keyed on
its ``<dt id="...">`` so the chunk deep-links to the exact docs anchor.
Prose between API entries is accumulated and chunked at section boundaries.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString, Tag

from app.core.constants import DOCS_BASE_URL

from .models import Chunk

_API_DL_CLASSES: frozenset[str] = frozenset(
    {
        "function",
        "class",
        "method",
        "attribute",
        "data",
        "exception",
        "decorator",
        "staticmethod",
        "classmethod",
        "property",
    }
)


def parse_docs_page(
    html: str,
    *,
    doc_path: str,
    module: str,
    version_minor: str,
) -> list[Chunk]:
    soup = BeautifulSoup(html, "lxml")
    base_url = f"{DOCS_BASE_URL}/{version_minor}/{doc_path}"
    main = soup.select_one("div[role=main]") or soup.select_one("div.body")
    if main is None:
        return []

    chunks: list[Chunk] = []
    for sec in main.find_all("section", recursive=False):
        chunks.extend(_walk_section(sec, [], base_url, module))
    return chunks


def _walk_section(
    section: Tag,
    parent_headings: list[str],
    base_url: str,
    module: str,
) -> list[Chunk]:
    heading = _section_heading(section)
    heading_path = [*parent_headings, heading] if heading else list(parent_headings)
    anchor = section.get("id", "") or ""

    chunks: list[Chunk] = []
    prose_parts: list[str] = []

    def flush_prose() -> None:
        text = "\n\n".join(p for p in prose_parts if p.strip()).strip()
        if text:
            chunks.append(
                Chunk(
                    content=text,
                    heading_path=heading_path,
                    source_url=_url_with_anchor(base_url, anchor),
                    module=module,
                    kind="prose",
                    anchor=anchor,
                )
            )

    for child in section.children:
        if isinstance(child, NavigableString) or not isinstance(child, Tag):
            continue
        if child.name == "section":
            flush_prose()
            prose_parts.clear()
            chunks.extend(_walk_section(child, heading_path, base_url, module))
        elif child.name == "dl" and _is_api_dl(child):
            flush_prose()
            prose_parts.clear()
            api = _api_chunk(child, heading_path, base_url, module)
            if api is not None:
                chunks.append(api)
        elif child.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            continue
        else:
            rendered = _render(child)
            if rendered:
                prose_parts.append(rendered)

    flush_prose()
    return chunks


def _section_heading(section: Tag) -> str:
    for name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        h = section.find(name, recursive=False)
        if h is not None:
            return _clean_heading(h.get_text(" ", strip=True))
    return ""


def _clean_heading(text: str) -> str:
    return text.rstrip("¶").strip()


def _is_api_dl(tag: Tag) -> bool:
    classes = tag.get("class") or []
    if "py" not in classes:
        return False
    return any(c in _API_DL_CLASSES for c in classes)


def _api_chunk(
    dl: Tag,
    heading_path: list[str],
    base_url: str,
    module: str,
) -> Chunk | None:
    dts = dl.find_all("dt", recursive=False)
    dds = dl.find_all("dd", recursive=False)
    if not dts:
        return None

    signatures = [_clean_heading(dt.get_text(" ", strip=True)) for dt in dts]
    description_parts: list[str] = []
    for dd in dds:
        for child in dd.children:
            if isinstance(child, Tag):
                rendered = _render(child)
                if rendered:
                    description_parts.append(rendered)

    anchor = dts[0].get("id", "") or ""
    content = ("\n".join(signatures) + "\n\n" + "\n\n".join(description_parts)).strip()
    if not content:
        return None

    return Chunk(
        content=content,
        heading_path=heading_path,
        source_url=_url_with_anchor(base_url, anchor),
        module=module,
        kind="api",
        anchor=anchor,
    )


def _render(tag: Tag) -> str:
    if tag.name == "pre":
        return f"```python\n{tag.get_text('', strip=False).rstrip()}\n```"
    # Sphinx wraps some admonitions in divs that contain nested <pre>;
    # render children individually so the fences survive.
    if tag.name == "div" and tag.find("pre", recursive=False):
        parts = [_render(c) for c in tag.children if isinstance(c, Tag)]
        return "\n\n".join(p for p in parts if p)
    return tag.get_text(" ", strip=True).rstrip("¶").strip()


def _url_with_anchor(base_url: str, anchor: str) -> str:
    return f"{base_url}#{anchor}" if anchor else base_url
