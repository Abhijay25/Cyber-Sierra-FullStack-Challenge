# Cyber Sierra FullStack Challenge

An AI-powered CSV/Excel analyser. Upload spreadsheets, preview data, and ask natural language questions answered by an OpenAI + PandasAI pipeline. Supports follow-up questions, per-session preference learning from feedback, and prompt history.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 (App Router, TypeScript, TanStack Table, SWR) |
| Backend | FastAPI (Python, uv) |
| AI | OpenAI GPT-4o → PandasAI  |
| Storage | In-memory DataFrames (session) + SQLite (history, preferences) |

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- [Node.js + yarn](https://yarnpkg.com/)
- An OpenAI API key

## Setup

```bash
cp backend/.env.example backend/.env
# then edit backend/.env and set OPENAI_API_KEY=your-key-here
```

## Running locally

```bash
make dev
```

Starts FastAPI on `http://localhost:8000` and Next.js on `http://localhost:3000`.

## Usage

1. Upload one or more `.csv`, `.xls`, or `.xlsx` files using the drop zone
2. Select a sheet tab to preview data — each tab maintains its own independent chat history
3. Delete a sheet with the × button on its tab; auto-switches to the next available sheet
4. Set **Rows to analyse** in the header to control how many rows the AI sees
5. Type a question and press Send — follow-up questions retain conversation context per sheet
6. Thumbs down with a comment updates your session's style preferences for future answers
7. Click **📋 History** to browse and re-use previous prompts

## Architecture

```
Browser
  └── Next.js (localhost:3000)
        └── FastAPI (localhost:8000)
              ├── /api/upload             parse files, store DataFrames
              ├── /api/sheets             list sheet metadata
              ├── /api/data/{sheet}       preview N rows
              ├── /api/query              run AI pipeline, save to SQLite
              ├── /api/feedback           record thumbs up/down, update prefs
              ├── /api/history            retrieve past prompts
              └── DELETE /api/sheets/{s}  remove a sheet from the session
```

### AI pipeline (per query)

1. **Rewrite** — GPT-4o rewrites the question as a precise pandas instruction, resolving follow-up references using conversation history
2. **PandasAI** — executes the instruction against the DataFrame via DuckDB SQL internally; agent is cached per `(session_id, sheet_name, row_count)` and reused across queries
3. **Fallback** — if PandasAI fails: context stuffing for ≤100 rows, simplified prompt retry for larger datasets
4. **Format** — GPT-4o formats the raw result into a natural language answer, applying user style preferences

### Session model

- Identity: UUID `session_id` stored as an `HttpOnly`, `SameSite=Strict` cookie (24h expiry)
- DataFrames: in-memory dict, evicted after 24h inactivity; capped at 15 sheets per session
- History + preferences: SQLite (`backend/mydatabase.db`)

## Security

- `OPENAI_API_KEY` is server-side only, never returned to the client
- Cookie is `HttpOnly` + `SameSite=Strict`; set `ENVIRONMENT=production` in `.env` to enable `Secure` flag (required for HTTPS)
- File uploads validated by extension, MIME type, and size (10 MB max, 10 files max)
- Filenames sanitised before use as keys
- All DB queries use SQLAlchemy ORM — no raw SQL string interpolation
- Feedback endpoint verifies prompt ownership before updating; comments capped at 200 characters
- Rate limiting: query 20 req/min, sheets 60 req/min, data 120 req/min per IP
- Query undergoes basic sanitisation; further protection via OpenAI's built-in content guardrails
- **Relevance gate**: the rewrite step (GPT-4o) checks whether the question can be answered from the uploaded dataset's columns before running PandasAI. Off-topic questions (e.g. "capital of France?") and references to non-existent columns (e.g. "average salary") are rejected with a clear explanation rather than hallucinated answers or silent column remapping
- `@tanstack/react-table` was audited against the May 11 2026 Shai-Hulud npm supply chain attack (CVE-2026-45321) — the `@tanstack/table*` family was confirmed clean; only the router/start ecosystem was compromised

## Performance

- **PandasAI agent cache**: agents are instantiated once per `(session_id, sheet_name, row_count)` tuple and reused for subsequent queries, avoiding the overhead of re-creating the agent on every request. The cache is invalidated when files are re-uploaded or the session is evicted.
- **Memory cap**: sessions are limited to 15 sheets to bound in-memory DataFrame storage. Parsed DataFrames can be significantly larger than the source file (NumPy array overhead, object dtype strings), so the cap prevents unbounded RAM growth under concurrent usage. Users can delete individual sheets via the UI to free capacity.

## Production deployment

Set in `backend/.env`:
```
ENVIRONMENT=production
OPENAI_API_KEY=your-key-here
```

Build the frontend and copy into the backend static directory:
```bash
make build
```

Then run:
```bash
make start
```

FastAPI serves both the API and the built Next.js frontend from the same origin — no CORS configuration needed.

## Running tests

```bash
cd backend
LD_LIBRARY_PATH=$(nix-shell -p zlib gcc.lib --run 'echo $LD_LIBRARY_PATH' 2>/dev/null || \
  echo "/nix/store/si4q3zks5mn5jhzzyri9hhd3cv789vlm-gcc-15.2.0-lib/lib:/nix/store/ri9paa3mri4kqakljak8ldvbcp7lpmif-zlib-1.3.1/lib") \
  uv run pytest tests/ -v
```

On non-NixOS systems simply `cd backend && uv run pytest tests/ -v`.
