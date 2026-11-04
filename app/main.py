import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from psycopg_pool import ConnectionPool

from app.core.config import settings
from app.infrastructure.postgres import (
    RepositorioUsuarioPostgres,
    RepositoriosPostgres,
)
from app.routers.auth import router as auth_router
from app.routers.web import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = None
    db_url = settings.DATABASE_URL
    if db_url:
        try:
            pool = ConnectionPool(
                conninfo=db_url,
                min_size=1,
                max_size=int(os.getenv("DB_POOL_SIZE", "5")),
                open=False,
            )
            pool.open(wait=False)
            db = RepositoriosPostgres(pool)
            app.state.db_pool = pool
            app.state.db = db
            app.state.repositorio_usuario = RepositorioUsuarioPostgres(db)
        except Exception:
            pool = None
    yield
    if pool is not None:
        try:
            pool.close()
        except Exception:
            pass


app = FastAPI(
    title="Trivialists",
    description="Plataforma de gestão de cardápios e pedidos de refeições individuais para o Impatech.",
    version="0.1.0",
    lifespan=lifespan,
)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"
app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")

app.include_router(auth_router)
app.include_router(web_router)


@app.get("/health", tags=["Health Check"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "Trivialists"}
