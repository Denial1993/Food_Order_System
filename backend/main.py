from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database import Base, engine
from routers import api_router, ws_router

import models  # noqa: F401  -- ensure all models are registered on Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 啟動時顯示環境資訊，方便確認目前接的是哪個 DB ──────────
    is_prod = bool(settings.DATABASE_URL)
    db_hint = (
        f"Supabase ({settings.DATABASE_URL.split('@')[-1].split('/')[0]})"
        if is_prod else
        f"Docker  ({settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME})"
    )
    print("=" * 55)
    print(f"  APP : {settings.APP_NAME}")
    print(f"  ENV : {settings.APP_ENV.upper()}")
    print(f"  DB  : {db_hint}")
    print(f"  DEBUG: {settings.DEBUG}")
    print("=" * 55)

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.APP_NAME, "status": "ok"}


@app.get("/health")
def health() -> dict:
    return {
        "status":  "healthy",
        "env":     settings.APP_ENV,
        "db_type": "supabase" if settings.DATABASE_URL else "docker",
    }
