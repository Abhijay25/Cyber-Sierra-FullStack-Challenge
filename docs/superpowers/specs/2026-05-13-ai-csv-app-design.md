# AI-Powered CSV/Excel Analyser — Design Spec

## Context

This is a take-home coding challenge for a backend engineer role at Cyber Sierra. The app lets users upload one or more CSV/XLS/XLSX files, preview their data, and ask natural language questions about it via an AI pipeline. The challenge explicitly evaluates thought process, security considerations, and the balance between optimisation and simplicity. The Titanic dataset (891 rows) will be used during the interview.

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router, TypeScript, TanStack Table) |
| Backend | FastAPI (Python, uv) |
| AI — primary | OpenAI GPT-4o (prompt reformulation) → PandasAI (code gen + execution) |
| AI — fallback | OpenAI GPT-4o context stuffing (≤100 rows) / PandasAI retry (>100 rows) |
| Persistence | SQLite via SQLAlchemy (prompt history + feedback) |
| In-memory store | Python dict `{session_id: {sheet_name: DataFrame}}` — replaced by disk storage in Phase 2 |
| Preferences | Per-session markdown in SQLite; prepended to every OpenAI reformulation call; updated via OpenAI on downvote + comment |
| Package managers | `yarn` (frontend), `uv` (backend) |

In production, FastAPI serves the built Next.js static files — single server, no CORS required, single command to run.

### Build Phases

**Phase 1 (now):** Core functionality — file upload, data preview, AI query pipeline, prompt history, feedback, and per-user preferences markdown fed into the AI pipeline.
**Phase 2 (later):** Persistence — files saved to disk, 3-session retention policy, DataFrames survive server restarts.

---

## Project Structure

```
/
├── Makefile                  # make dev, make build, make start
├── .gitignore                # .env, __pycache__, node_modules, .next
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   └── page.tsx          # single-page app shell
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── SheetTabs.tsx
│   │   ├── DataPreview.tsx   # N-rows input + TanStack Table
│   │   ├── QueryInterface.tsx # chat input + answer display + feedback
│   │   └── HistoryPanel.tsx  # floating fixed panel with prev/next cycling
│   └── lib/
│       └── api.ts            # typed fetch wrappers for all endpoints
└── backend/
    ├── main.py               # FastAPI app, CORS, static file mount
    ├── routers/
    │   ├── upload.py
    │   ├── data.py
    │   ├── query.py
    │   ├── history.py
    │   └── feedback.py
    ├── services/
    │   ├── session_store.py  # in-memory DataFrame store
    │   ├── ai_pipeline.py    # OpenAI reformulate → PandasAI → fallback
    │   └── db.py             # SQLAlchemy setup + models
    ├── models.py             # Pydantic request/response schemas
    ├── .env                  # OPENAI_API_KEY (never committed)
    └── pyproject.toml
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload` | Multipart file upload; parses with pandas; stores DataFrames in session store; sets `session_id` HttpOnly cookie |
| `GET` | `/api/sheets` | Reads `session_id` from cookie; returns `[{name, row_count, columns}]` for all loaded sheets |
| `GET` | `/api/data/{sheet}?n=N` | Reads `session_id` from cookie; returns top N rows of named sheet as JSON |
| `POST` | `/api/query` | Reads `session_id` from cookie; runs AI pipeline; persists to SQLite; returns answer |
| `GET` | `/api/history` | Reads `session_id` from cookie; returns past prompts ordered by `created_at desc` |
| `POST` | `/api/feedback` | Sets `feedback` field (`up`/`down`) on a prompt record by `prompt_id` |

All responses use consistent `{data, error}` envelope. All errors return appropriate HTTP status codes (400 for bad input, 422 for validation, 500 for pipeline failures).

---

## Data Model

Phase 1 — two tables:

```sql
CREATE TABLE prompts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    sheet_name     TEXT NOT NULL,
    question       TEXT NOT NULL,
    refined_prompt TEXT,
    answer         TEXT NOT NULL,
    feedback       TEXT,          -- 'up', 'down', or NULL
    comment        TEXT,          -- one-liner from user on downvote
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    session_id     TEXT PRIMARY KEY,
    preferences_md TEXT DEFAULT '',   -- updated by OpenAI on each downvote+comment
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Phase 2 additions: file retention tracking columns on `sessions`.

---

## AI Pipeline

```
User question
  └─► Step 1: OpenAI GPT-4o
        Prompt: "Rewrite this question as a precise, pandas-friendly instruction
                 for a DataFrame with columns {cols}. Return only the rewritten
                 instruction."
        Output: refined_prompt (saved to DB)
  └─► Step 2: PandasAI
        Input: refined_prompt + DataFrame
        Output: answer string or raises exception
  └─► On success: return answer
  └─► On failure:
        Show retry toast to user
        if row_count ≤ 100:
          Step 3a: OpenAI context stuffing
            Send top 100 rows as CSV text + original question
            Return natural language answer
        else:
          Step 3b: PandasAI retry
            Strip conversational framing from the original question;
            restate it as a single direct computation (e.g. "calculate
            the mean of column X grouped by column Y"). Send to PandasAI.
            If still fails: return "Could not compute answer for this question"
```

---

## Frontend UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ [Upload Files]  [titanic.csv]  [sales.xlsx › Sheet2]    │  ← file/sheet tabs
├─────────────────────────────────────────────────────────┤
│  Show top [ 10 ] rows                                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ PassengerId │ Survived │ Pclass │ Name │ ...     │   │  ← TanStack Table
│  │     ...     │    ...   │  ...   │ ...  │         │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Answer: 38.4% of passengers survived.   [👍]  [👎]    │
│  ─────────────────────────────────────────────────────  │
│  Ask a question about titanic.csv...          [Send]    │
│                                    [📋 History]         │
└─────────────────────────────────────────────────────────┘

                          ┌─ History (floating, fixed bottom-right) ──┐
                          │  Prompt History                    [×]    │
                          │  ◀  3 of 7  ▶                            │
                          │  ───────────────────────────────────────  │
                          │  Q: What is the survival rate?            │
                          │  A: 38.4% of passengers survived.         │
                          │  Sheet: titanic.csv   [👍]  [Re-use]      │
                          └───────────────────────────────────────────┘
```

- History panel is `position: fixed`, toggled by the History button
- Prev/Next arrows cycle through prompts; panel is also scrollable
- Re-use populates the chat input with the selected question
- Feedback shown inline; submits via `POST /api/feedback`
- History persists across tab switches (all sheets in one list)

---

## Security Considerations

| Concern | Mitigation |
|---|---|
| API key exposure | `OPENAI_API_KEY` in `.env`, never in frontend bundle, `.env` in `.gitignore` |
| Session hijacking | `session_id` as `HttpOnly`, `SameSite=Lax` cookie — not accessible to JS |
| CORS | In dev: whitelist `localhost:3000`; in prod: not needed (same origin) |
| File type abuse | Validate extension (`.csv`, `.xls`, `.xlsx`) and MIME type on upload |
| File size abuse | 10 MB cap per file; reject early before pandas parsing |
| Code execution | PandasAI executes generated code; scoped to in-memory DataFrame only, no filesystem access |
| SQL injection | SQLAlchemy ORM with parameterised queries throughout |
| Sensitive data in logs | Never log question content or API key values |

---

## Local Development

```bash
make dev        # starts FastAPI (port 8000) and Next.js (port 3000) concurrently
make build      # builds Next.js static output into backend/static/
make start      # starts FastAPI only, serving built static files (single server)
```

`.env` in `backend/`:
```
OPENAI_API_KEY=<your key here>
```

---

## Verification

1. `make dev` — both servers start without errors
2. Upload `titanic.csv` — tabs appear, top 10 rows render in table
3. Change N to 50 — table updates
4. Ask "What is the survival rate?" — answer returns (PandasAI path, 891 rows)
5. Ask same question on a <100 row file — answer returns via fallback path
6. Thumbs up an answer — feedback persists after page refresh (re-fetched from SQLite)
7. Open history panel — past prompts visible, prev/next cycles, Re-use populates input
8. Check `/docs` (FastAPI Swagger) — all endpoints documented with correct schemas
9. Verify `.env` is not tracked: `git status` shows no `.env` file
