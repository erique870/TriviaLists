import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg import OperationalError
from psycopg.errors import UniqueViolation
from psycopg_pool import ConnectionPool, PoolTimeout

from app.application.notificacao_service import ServicoNotificacao
from app.application.restaurante_service import ServicoRestaurante
from app.core.clock import agora
from app.core.config import settings
from app.domain import ErroDominio
from app.infrastructure.contexto import contexto_memoria, contexto_postgres
from app.infrastructure.postgres import RepositoriosPostgres
from app.routers.auth import router as auth_router
from app.routers.operacoes import router as operacoes_router
from app.routers.web import router as web_router

logger = logging.getLogger(__name__)


def executar_rotinas(ctx):
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao)
    servico.encerrar_expiradas(agora())
    ServicoNotificacao(ctx).processar()


async def trabalhador(ctx, parar):
    while not parar.is_set():
        try:
            await asyncio.to_thread(executar_rotinas, ctx)
        except Exception:
            logger.exception("Falha na rotina periódica de fechamento/notificação; haverá nova tentativa.")
        try:
            await asyncio.wait_for(parar.wait(), timeout=settings.WORKER_INTERVAL_SECONDS)
        except TimeoutError:
            pass


def create_app(contexto=None, executar_tarefas=True):
    @asynccontextmanager
    async def lifespan(app):
        pool = None
        if contexto is not None:
            ctx = contexto
        elif settings.DATABASE_URL:
            pool = ConnectionPool(settings.DATABASE_URL, min_size=1,
                                  max_size=int(os.getenv("DB_POOL_SIZE", "5")), timeout=5, open=False)
            try:
                pool.open(wait=True, timeout=5)
            except Exception:
                pool.close()
                raise
            ctx = contexto_postgres(RepositoriosPostgres(pool))
        else:
            ctx = contexto_memoria()
            if os.getenv("APP_DEMO", "").lower() == "true":
                from app.infrastructure.demo import carregar_demo
                carregar_demo(ctx)
        app.state.contexto = ctx
        parar = asyncio.Event()
        tarefa = asyncio.create_task(trabalhador(ctx, parar)) if executar_tarefas else None
        try:
            yield
        finally:
            parar.set()
            if tarefa is not None:
                await tarefa
            if pool is not None:
                pool.close()

    app = FastAPI(title="Trivialists", version="0.2.0",
                  description="Gestão de cardápios e pedidos de refeições do Impatech.", lifespan=lifespan)

    @app.exception_handler(ErroDominio)
    async def erro_dominio(request: Request, erro: ErroDominio):
        codigo = erro.codigo
        status = 422
        if codigo in {"acesso_negado", "horario_limite_excedido"}:
            status = 403
        elif codigo.endswith("nao_encontrado") or codigo.endswith("nao_encontrada"):
            status = 404
        elif codigo in {"pedido_ativo_existente", "lista_fechada", "pedido_ja_cancelado", "lista_ainda_aberta", "lista_ainda_nao_aberta", "produto_em_uso", "pedido_cancelado", "pedido_ja_retirado"}:
            status = 409
        return JSONResponse(status_code=status, content={"detail": erro.mensagem, **erro.to_dict()})

    @app.exception_handler(UniqueViolation)
    async def conflito(request: Request, erro):
        return JSONResponse(status_code=409, content={"detail": "Já existe um registro com estes dados."})

    async def banco_indisponivel(request: Request, erro):
        logger.error("Banco de dados indisponível: %s", type(erro).__name__)
        return JSONResponse(status_code=503, content={"detail": "Banco de dados temporariamente indisponível."})

    app.add_exception_handler(PoolTimeout, banco_indisponivel)
    app.add_exception_handler(OperationalError, banco_indisponivel)
    public = Path(__file__).resolve().parent.parent / "public"
    app.mount("/static", StaticFiles(directory=str(public)), name="static")
    app.include_router(auth_router)
    app.include_router(operacoes_router)
    app.include_router(web_router)

    @app.get("/health", tags=["Health Check"])
    def health_check():
        return {"status": "ok", "app": "Trivialists"}

    return app


app = create_app()
