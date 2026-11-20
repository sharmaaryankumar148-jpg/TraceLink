import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app import cache
from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import auth, complaints, insights
from app.security import ensure_bootstrap_user

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        ensure_bootstrap_user(db)
    yield


app = FastAPI(
    title="TraceLink",
    description=(
        "Cyber complaint triage and linking. Classifies complaints, extracts suspect identifiers "
        "(phone, UPI, account, email, URL), scores urgency with reasons, and links complaints that "
        "share an identifier.\n\n**Prototype: synthetic data only.**"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(insights.router)


@app.get("/health", tags=["system"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    redis_ok = cache.get_client() is not None
    return {
        "status": "ok",
        "queue_mode": "redis" if redis_ok else "inline",
        "queue_length": cache.queue_length(),
        "llm_enabled": bool(settings.gemini_api_key),
    }
