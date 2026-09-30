from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: DbSession) -> dict:
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
    }
