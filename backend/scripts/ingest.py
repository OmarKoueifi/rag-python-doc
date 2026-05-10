"""Download the Python docs archive, parse + chunk, embed, upsert into Chroma."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from openai import OpenAI

from app.core.config import BACKEND_ROOT, get_settings
from app.rag.archive import (
    download_archive,
    extract_module_pages,
    major_minor,
    module_for_doc_path,
)
from app.rag.chunker import resize_chunks
from app.rag.indexer import Indexer
from app.rag.models import Chunk
from app.rag.parser import parse_docs_page

RAW_DIR = BACKEND_ROOT / "data" / "raw"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest Python docs into ChromaDB.")
    p.add_argument("--version", help="Override PYTHON_DOCS_VERSION (e.g. 3.12.7)")
    p.add_argument("--modules", help="Override PYTHON_DOCS_MODULES (comma-separated)")
    p.add_argument("--rebuild", action="store_true", help="Drop the collection first")
    p.add_argument("--dry-run", action="store_true", help="Parse + chunk only")
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    settings = get_settings()
    version = args.version or settings.python_docs_version
    modules = (
        [m.strip() for m in args.modules.split(",") if m.strip()]
        if args.modules
        else settings.modules_list
    )
    vm = major_minor(version)

    print(f"→ Python docs {version} (URL segment {vm})")
    print(f"→ Modules: {', '.join(modules)}")
    print(f"→ Chroma at {settings.chroma_path_abs}\n")

    started = time.monotonic()

    archive_path = RAW_DIR / f"python-{version}-docs-html.zip"
    print(f"[1/5] Archive: {archive_path.name}")
    if archive_path.exists():
        print(f"      cached ({archive_path.stat().st_size // (1 << 20)} MB)")
    else:
        print("      downloading…")
        download_archive(version, archive_path)
        print(f"      done ({archive_path.stat().st_size // (1 << 20)} MB)")

    html_dir = RAW_DIR / "html" / version
    print(f"[2/5] Extracting pages into {html_dir.relative_to(BACKEND_ROOT)}")
    pages = extract_module_pages(archive_path, modules, html_dir)
    if not pages:
        print(f"!! No pages matched modules={modules}. Archive layout may have changed.")
        return 1
    for rel in sorted(pages):
        print(f"      - {rel}")

    print(f"[3/5] Parsing {len(pages)} page(s)")
    raw_chunks: list[Chunk] = []
    for rel, path in sorted(pages.items()):
        module = module_for_doc_path(rel, modules)
        page_chunks = parse_docs_page(
            path.read_text(encoding="utf-8"),
            doc_path=rel,
            module=module,
            version_minor=vm,
        )
        print(f"      {rel} → {len(page_chunks)} chunks")
        raw_chunks.extend(page_chunks)
    print(f"      raw total: {len(raw_chunks)}")

    chunks = resize_chunks(raw_chunks)
    api_count = sum(1 for c in chunks if c.kind == "api")
    prose_count = len(chunks) - api_count
    print(f"      after resize: {len(chunks)} (api: {api_count}, prose: {prose_count})")

    if args.dry_run:
        print("\n→ --dry-run: skipping embed + index.")
        _preview(chunks)
        return 0

    print(f"[4/5] Embedding with {settings.openai_embedding_model} and indexing")
    indexer = Indexer(
        chroma_path=settings.chroma_path_abs,
        collection_name=settings.chroma_collection,
        embed_model=settings.openai_embedding_model,
        openai_client=OpenAI(api_key=settings.openai_api_key),
    )
    if args.rebuild:
        print(f"      --rebuild: dropping collection '{settings.chroma_collection}'")
        indexer.reset()

    indexed = indexer.index(
        chunks,
        on_batch=lambda done, total: print(f"      embedded {done}/{total}"),
    )

    print("[5/5] Writing manifest")
    manifest = {
        "version": version,
        "version_minor": vm,
        "modules": modules,
        "chunk_count": indexed,
        "api_chunks": api_count,
        "prose_chunks": prose_count,
        "pages_ingested": sorted(pages),
        "embedding_model": settings.openai_embedding_model,
        "chroma_collection": settings.chroma_collection,
        "indexed_at": datetime.now(UTC).isoformat(),
    }
    manifest_path = settings.chroma_path_abs / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"      wrote {manifest_path.relative_to(BACKEND_ROOT)}")

    print(f"\n✓ Ingest complete in {time.monotonic() - started:.1f}s ({indexed} chunks)")
    return 0


def _preview(chunks: list[Chunk], n: int = 5) -> None:
    print("\n--- Chunk preview ---")
    for c in chunks[:n]:
        print(f"\n[{c.kind}] {c.heading_breadcrumb}")
        print(f"  {c.source_url}")
        print(f"  {c.content[:200].replace(chr(10), ' ')}…")


if __name__ == "__main__":
    sys.exit(main())
