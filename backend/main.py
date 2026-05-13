from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # must run before any module that reads env vars at import time

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services.db import Base, engine
from routers import upload, data, query, history, feedback

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="CSV Analyser API", lifespan=lifespan)

# CORS — dev only: allow Next.js on :3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api prefix
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(data.router, prefix="/api", tags=["data"])
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])

# Prod: serve built Next.js static files from backend/static/
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
