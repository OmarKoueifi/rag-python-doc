from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from app.core.constants import ARCHIVE_URL_TEMPLATE

# Match a module prefix but are just TOCs — skip so they don't pollute retrieval.
SKIP_PAGES: frozenset[str] = frozenset(
    {
        "asyncio-api-index.html",
        "asyncio-llapi-index.html",
    }
)


def major_minor(version: str) -> str:
    parts = version.split(".")
    if len(parts) < 2:
        raise ValueError(f"Expected X.Y.Z version, got: {version!r}")
    return f"{parts[0]}.{parts[1]}"


def archive_url(version: str) -> str:
    return ARCHIVE_URL_TEMPLATE.format(major_minor=major_minor(version), version=version)


def download_archive(version: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", archive_url(version), follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=1 << 15):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def extract_module_pages(
    archive: Path, modules: list[str], out_dir: Path
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}
    with zipfile.ZipFile(archive) as z:
        root = _archive_root(z)
        for name in z.namelist():
            if not name.startswith(root):
                continue
            rel = name[len(root) :]
            if not rel.startswith("library/") or not rel.endswith(".html"):
                continue
            basename = Path(rel).name
            if basename in SKIP_PAGES or not _matches_any_module(basename, modules):
                continue
            target = out_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, target.open("wb") as dst:
                dst.write(src.read())
            results[rel] = target
    return results


def module_for_doc_path(doc_path: str, modules: list[str]) -> str:
    basename = Path(doc_path).name
    for mod in modules:
        if _matches_module(basename, mod):
            return mod
    return modules[0]


def _matches_any_module(basename: str, modules: list[str]) -> bool:
    return any(_matches_module(basename, m) for m in modules)


def _matches_module(basename: str, module: str) -> bool:
    stem = basename.removesuffix(".html")
    return stem == module or stem.startswith(f"{module}-") or stem.startswith(f"{module}.")


def _archive_root(z: zipfile.ZipFile) -> str:
    for name in z.namelist():
        slash = name.find("/")
        if slash > 0:
            return name[: slash + 1]
    return ""
