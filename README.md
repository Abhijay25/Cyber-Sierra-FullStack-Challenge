# Cyber Sierra FullStack Challenge

An AI-powered CSV/Excel analyser. Upload spreadsheets, preview data, and ask natural language questions answered by an OpenAI + PandasAI pipeline. Supports follow-up questions, per-session preference learning from feedback, and prompt history.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 15 (App Router, TypeScript, TanStack Table, SWR) |
| Backend | FastAPI (Python, uv) |
| AI | OpenAI GPT-4o → PandasAI → fallback (context stuffing / retry) |
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
2. Select a sheet tab to preview data
3. Set **Rows to analyse** in the header to control how many rows the AI sees
4. Type a question and press Send — follow-up questions retain conversation context
5. Thumbs down with a comment updates your session's style preferences for future answers
6. Click **📋 History** to browse and re-use previous prompts

## Architecture

```
Browser
  └── Next.js (localhost:3000)
        └── fetch() with credentials
              └── FastAPI (localhost:8000)
                    ├── /api/upload     — parse files, store DataFrames in memory
                    ├── /api/sheets     — list sheet metadata for session
                    ├── /api/data/{sheet} — preview N rows
                    ├── /api/query      — run AI pipeline, persist to SQLite
                    ├── /api/feedback   — save thumbs up/down, update preferences
                    └── /api/history    — retrieve past prompts for session
```

### AI pipeline (per query)

1. **Rewrite** — GPT-4o rewrites the question as a precise pandas instruction, resolving follow-up references using conversation history
2. **PandasAI** — executes the instruction against the DataFrame via DuckDB SQL internally
3. **Fallback** — if PandasAI fails: context stuffing for ≤100 rows, simplified prompt retry for larger datasets
4. **Format** — GPT-4o formats the raw result into a natural language answer, applying user style preferences

### Session model

- Identity: UUID `session_id` stored as an `HttpOnly`, `SameSite=Lax` cookie (24h expiry)
- DataFrames: in-memory dict, evicted after 24h inactivity
- History + preferences: SQLite (`backend/mydatabase.db`)

## Security

- `OPENAI_API_KEY` is server-side only, never returned to the client
- Cookie is `HttpOnly` + `SameSite=Lax`; set `ENVIRONMENT=production` in `.env` to enable `Secure` flag (required for HTTPS)
- File uploads validated by extension, MIME type, and size (10 MB max, 10 files max)
- Filenames sanitised before use as keys
- All DB queries use SQLAlchemy ORM — no raw SQL string interpolation
- Feedback endpoint verifies prompt ownership before updating
- Query endpoint rate-limited to 20 requests/minute per IP

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
