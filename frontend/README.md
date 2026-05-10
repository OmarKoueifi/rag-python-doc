# Frontend

React + TypeScript (strict) + Vite + Tailwind. Two pages: public chat (`/`)
and password-protected admin dashboard (`/admin`).

## Setup

```bash
npm install
npm run dev           # http://localhost:5173 (proxies /api → localhost:8000)
npm run build         # strict tsc + vite build → dist/
npm run typecheck     # tsc --noEmit
```

The dev server proxies `/api/*` and `/healthz` to the FastAPI backend at
`http://localhost:8000` (see `vite.config.ts`). Start the backend first:

```bash
cd ../backend && uvicorn app.main:app --reload
```

## Structure

```
src/
  main.tsx              entrypoint, router root
  App.tsx               3 routes: /, /admin/login, /admin
  index.css             Tailwind base + prose-chat styles + hljs theme
  lib/
    types.ts            mirrors backend Pydantic schemas
    api.ts              typed fetch wrappers (credentials: include)
    sse.ts              fetch-based SSE parser for /api/chat
  components/
    ChatMessage.tsx     user + assistant bubbles, markdown + citations
    admin/              dashboard widgets (cards, chart, tables)
  pages/
    Chat.tsx            public chat
    AdminLogin.tsx      password form
    AdminDashboard.tsx  metrics + questions + flagged
```

## Design notes

- **Streaming** uses `fetch` + `ReadableStream` + a small manual SSE parser
  (see `lib/sse.ts`) — `EventSource` doesn't support POST or cookies.
- **Cookies** (`session_id`, `admin_session`) are HTTP-only; we rely on the
  browser's credentialed-fetch behavior and same-origin routing in prod.
- **Markdown answer rendering** uses `react-markdown` + `remark-gfm` +
  `rehype-highlight` so Python fenced code blocks get syntax highlighting.
