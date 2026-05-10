# Backend

FastAPI + LlamaIndex + ChromaDB. See the root `README.md` for the full project overview, architecture, and design tradeoffs. This file is the developer cheat-sheet.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Dev tooling
pip install -r requirements-dev.txt
```

Environment variables are loaded from a `.env` file at the repo root
(see `../.env.example`).

## Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs at `http://localhost:8000/docs`.

## Ingest

One-shot build of the ChromaDB index from the official Python docs archive:

```bash
python scripts/ingest.py                         # use .env PYTHON_DOCS_VERSION
python scripts/ingest.py --version 3.12.7        # override
python scripts/ingest.py --rebuild               # drop existing collection first
python scripts/ingest.py --dry-run               # parse + chunk but don't embed
```

The script:

1. Downloads `python-X.Y.Z-docs-html.zip` from python.org (cached in `data/raw/`)
2. Extracts only the target module pages
3. Parses with BeautifulSoup, walks the `<section>` tree
4. Emits API-reference entries as their own chunks (`<dl class="py ...">`)
5. Chunks prose at section boundaries; splits long sections at `<p>`/`<pre>` never mid-code-block
6. Batches embeddings to OpenAI (100/request)
7. Upserts into Chroma with `source_url`, `heading_path`, `module`, `anchor` metadata
8. Writes `data/chroma/manifest.json` with version + chunk count + model

## Capture seed data

The admin dashboard ships pre-populated with real captured chat traffic.
`scripts/capture_seed.py` runs each demo prompt through the live pipeline
(moderation → retrieval → OpenAI → flag detection) and writes the result
to `data/seed_fixture.json`, which is committed. `scripts/seed_db.py` reads
that file. Re-run capture only when prompts, models, or chunks change.

```bash
python scripts/capture_seed.py            # ~$0.03 in OpenAI credit
python scripts/seed_db.py                 # idempotent, offline, free
python scripts/seed_db.py --reset         # wipe then re-seed
```

The lifespan auto-seeds on boot when `SEED_ON_STARTUP=true` and the DB is
empty — useful for fresh Render deploys.

## Evaluate retrieval

```bash
python scripts/eval.py              # run the golden suite
python scripts/eval.py --write-md   # regenerate EVAL_RESULTS.md at repo root
python scripts/eval.py --top-k 10   # override top-k
```

Each case declares expected anchor hits and a max rank. KNOWN FAIL cases are documented weaknesses (see each case's `known_issue` field) they don't fail the suite. Unknown regressions exit non-zero. See `EVAL_RESULTS.md` at the repo root for the current baseline.

## Deployment (Render)

- **Build command:** `pip install -r backend/requirements.txt`
- **Start command:** `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Environment:** set each variable from `.env.example`; `ENVIRONMENT=production`

The free tier has no persistent disk, so the ChromaDB index at
`backend/data/chroma/` is committed to the repository. To update the index, re-run `scripts/ingest.py --rebuild` locally and commit the result.

## Code style

```bash
ruff format .
ruff check . --fix
```
