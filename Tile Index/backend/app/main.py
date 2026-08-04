from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, catalog, inventory, invoices, reports, updates
from app.core.config import get_settings


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
    return {"status": "ok", "version": settings.app_version}


app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(inventory.router)
app.include_router(invoices.router)
app.include_router(reports.router)
app.include_router(updates.router)
