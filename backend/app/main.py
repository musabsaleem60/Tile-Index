import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from app.api import activity_log, auth, catalog, inventory, invoices, reports, stock, updates
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import TileRate


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health():
    with SessionLocal() as db:
        tile_rate_count = db.scalar(select(func.count(TileRate.id))) or 0
        alembic_version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    if tile_rate_count == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tile rate card is empty. Seed tile_rates before using production workflows.",
        )
    commit_sha = (
        os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("APP_GIT_SHA")
        or os.getenv("GIT_COMMIT")
        or "unknown"
    )
    return {
        "status": "ok",
        "version": settings.app_version,
        "commit_sha": commit_sha,
        "alembic_version": alembic_version,
        "tile_rates": tile_rate_count,
    }


app.include_router(auth.router)
app.include_router(activity_log.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(invoices.router)
app.include_router(reports.router)
app.include_router(stock.router)
app.include_router(updates.router)

