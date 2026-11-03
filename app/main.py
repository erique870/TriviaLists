import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from psycopg_pool import ConnectionPool

from app.application import ServicoPedido, ServicoRestaurante
from app.infrastructure.postgres import (
    RepositorioListaDiariaPostgres,
    RepositorioPedidoPostgres,
    RepositorioProdutoPostgres,
    RepositorioRestaurantePostgres,
    RepositorioUsuarioPostgres,
    RepositoriosPostgres,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = ConnectionPool(
        conninfo=os.getenv(
            "DATABASE_URL",
            "postgresql://trivialists:trivialists@localhost:5432/trivialists",
        ),
        min_size=1,
        max_size=int(os.getenv("DB_POOL_SIZE", "10")),
        open=False,
    )
    pool.open(wait=True)
    db = RepositoriosPostgres(pool)
    app.state.servico_restaurante = ServicoRestaurante(
        usuarios=RepositorioUsuarioPostgres(db),
        restaurantes=RepositorioRestaurantePostgres(db),
        produtos=RepositorioProdutoPostgres(db),
        listas=RepositorioListaDiariaPostgres(db),
    )
    app.state.servico_pedido = ServicoPedido(
        usuarios=RepositorioUsuarioPostgres(db),
        listas=RepositorioListaDiariaPostgres(db),
        pedidos=RepositorioPedidoPostgres(db),
    )
    app.state.db_pool = pool
    try:
        yield
    finally:
        pool.close()

app = FastAPI(
    title="Trivialists API",
    description="API para gestão de cardápios e pedidos de refeições.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", tags=["TesteDaSilva"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/database", tags=["health"])
def database_health(request: Request) -> dict[str, str]:
    with request.app.state.db_pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"database": "ok"}
