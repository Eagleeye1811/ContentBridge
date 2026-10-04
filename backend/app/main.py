"""FastAPI application factory for ContentBridge."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    auth,
    documents,
    facts,
    health,
    jobs,
    outputs,
    review,
    verification,
)
from app.config import settings

logging.basicConfig(level=settings.log_level)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.api_title,
        version="0.1.0",
        description=(
            "Source document -> RAG -> Source of Truth -> LLM -> Verification. "
            "One pipeline, many outputs."
        ),
    )

    cors_origins = settings.cors_origins or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?" if settings.app_env == "development" else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(jobs.router)
    app.include_router(facts.router)
    app.include_router(outputs.router)
    app.include_router(verification.router)
    app.include_router(review.router)
    app.include_router(admin.router)
    return app


app = create_app()
