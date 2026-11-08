"""Composição dos adaptadores usados pela API e pelas tarefas periódicas."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Callable, ContextManager

from app.application.ports import (
    RepositorioUsuario, RepositorioRestaurante, RepositorioProduto,
    RepositorioListaDiaria, RepositorioPedido, RepositorioNotificacao,
)

from app.application.repositories import (
    RepositorioListasEmMemoria, RepositorioPedidosEmMemoria,
    RepositorioProdutosEmMemoria, RepositorioRestaurantesEmMemoria,
    RepositorioUsuariosEmMemoria,
)


@dataclass
class ContextoPersistencia:
    usuarios: RepositorioUsuario
    restaurantes: RepositorioRestaurante
    produtos: RepositorioProduto
    listas: RepositorioListaDiaria
    pedidos: RepositorioPedido
    notificacoes: RepositorioNotificacao
    transacao: Callable[[], ContextManager]


def contexto_memoria():
    from app.infrastructure.notificacoes import NotificacoesEmMemoria

    usuarios = RepositorioUsuariosEmMemoria()
    restaurantes = RepositorioRestaurantesEmMemoria()
    produtos = RepositorioProdutosEmMemoria()
    listas = RepositorioListasEmMemoria(produtos=produtos)
    pedidos = RepositorioPedidosEmMemoria(listas)
    notificacoes = NotificacoesEmMemoria(usuarios, listas, restaurantes)
    lock = RLock()
    # Um único snapshot preserva referências compartilhadas e permite rollback.
    alvos = [(usuarios, "_usuarios"), (restaurantes, "_restaurantes"),
             (produtos, "_produtos"), (listas, "_listas"),
             (notificacoes, "eventos"), (notificacoes, "notificacoes")]

    @contextmanager
    def transacao():
        with lock:
            snapshot = deepcopy([getattr(obj, campo) for obj, campo in alvos])
            try:
                yield
            except Exception:
                for (obj, campo), valor in zip(alvos, snapshot):
                    setattr(obj, campo, valor)
                raise

    return ContextoPersistencia(usuarios, restaurantes, produtos, listas, pedidos, notificacoes, transacao)


def contexto_postgres(db):
    from app.infrastructure.postgres import (
        RepositorioUsuarioPostgres, RepositorioRestaurantePostgres,
        RepositorioProdutoPostgres, RepositorioListaDiariaPostgres, RepositorioPedidoPostgres,
    )
    from app.infrastructure.notificacoes import NotificacoesPostgres

    return ContextoPersistencia(
        RepositorioUsuarioPostgres(db), RepositorioRestaurantePostgres(db),
        RepositorioProdutoPostgres(db), RepositorioListaDiariaPostgres(db),
        RepositorioPedidoPostgres(db), NotificacoesPostgres(db), db.transacao,
    )
