"""Casos de uso de criação e cancelamento de pedidos."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.application.ports import RepositorioListaDiaria, RepositorioPedido, RepositorioUsuario
from app.domain import (
    AcessoNegadoError,
    ListaDiaria,
    Pedido,
    ValidacaoDeDominioError,
)


class ServicoPedido:
    def __init__(
        self,
        usuarios: RepositorioUsuario,
        listas: RepositorioListaDiaria,
        pedidos: RepositorioPedido,
    ) -> None:
        self.usuarios = usuarios
        self.listas = listas
        self.pedidos = pedidos

    def criar_pedido(
        self,
        aluno_id: int,
        lista_id: int,
        itens: Mapping[int, int],
        data_hora: datetime,
    ) -> Pedido:
        aluno = self.usuarios.obter_por_id(aluno_id)
        if aluno is None:
            raise AcessoNegadoError("Usuário não encontrado.")
        lista = self._obter_lista(lista_id)
        pedido = lista.criar_pedido(
            usuario=aluno,
            itens=itens,
            data_hora=data_hora,
            pedido_id=self.pedidos.proximo_id(),
        )
        self.pedidos.salvar(pedido)
        return pedido

    def cancelar_pedido(
        self, aluno_id: int, pedido_id: int, data_hora: datetime
    ) -> Pedido:
        pedido = self.pedidos.obter_por_id(pedido_id)
        if pedido is None:
            raise ValidacaoDeDominioError(
                "Pedido não encontrado.", codigo="pedido_nao_encontrado"
            )
        aluno = self.usuarios.obter_por_id(aluno_id)
        if aluno is None:
            raise AcessoNegadoError("Usuário não encontrado.")
        lista = self._obter_lista(pedido.lista_diaria_id)
        lista.cancelar_pedido(aluno, pedido_id, data_hora)
        pedido_atualizado = next(p for p in lista.pedidos if p.id == pedido_id)
        self.pedidos.salvar(pedido_atualizado)
        return pedido_atualizado

    def _obter_lista(self, lista_id: int) -> ListaDiaria:
        lista = self.listas.obter_por_id(lista_id)
        if lista is None:
            raise ValidacaoDeDominioError(
                "Lista diária não encontrada.", codigo="lista_nao_encontrada"
            )
        return lista
