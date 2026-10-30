"""Entidades e regras de negócio do domínio Trivialists."""

from app.domain.enums import (
    PapelUsuario,
    StatusLista,
    StatusPedido,
    StatusRetirada,
    TipoCardapio,
)
from app.domain.exceptions import (
    AcessoNegadoError,
    ErroDominio,
    HorarioLimiteExcedidoError,
    PedidoAtivoExistenteError,
    RegraDeNegocioError,
    ValidacaoDeDominioError,
)
from app.domain.item_pedido import ItemPedido
from app.domain.lista_diaria import ListaDiaria
from app.domain.pedido import Pedido
from app.domain.produto import Produto
from app.domain.restaurante import Restaurante
from app.domain.usuario import Usuario

__all__ = [
    "ItemPedido",
    "ListaDiaria",
    "Pedido",
    "PapelUsuario",
    "Produto",
    "AcessoNegadoError",
    "ErroDominio",
    "HorarioLimiteExcedidoError",
    "PedidoAtivoExistenteError",
    "RegraDeNegocioError",
    "Restaurante",
    "StatusLista",
    "StatusPedido",
    "StatusRetirada",
    "TipoCardapio",
    "Usuario",
    "ValidacaoDeDominioError",
]
