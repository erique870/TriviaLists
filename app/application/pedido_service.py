"""Casos de uso do cliente: CU01 visualizar, CU02 pedir e CU03 cancelar."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping

from app.application.ports import RepositorioListaDiaria, RepositorioPedido, RepositorioUsuario
from app.domain import (
    AcessoNegadoError,
    ListaDiaria,
    PapelUsuario,
    Pedido,
    Usuario,
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

    def listar_listas_abertas(
        self,
        aluno_id: int,
        data_hora: datetime,
        restaurante_id: int | None = None,
    ) -> list[ListaDiaria]:
        """CU01: lista cardápios abertos e ainda dentro do horário limite."""
        self._obter_aluno(aluno_id)
        if data_hora.utcoffset() is None:
            raise ValidacaoDeDominioError("A consulta precisa informar um fuso horário.")
        return self.listas.listar_abertas(data_hora, restaurante_id)

    def listar_meus_pedidos(self, aluno_id: int) -> list[Pedido]:
        """Retorna somente os pedidos do aluno autenticado (apoio ao CU03)."""
        self._obter_aluno(aluno_id)
        return self.pedidos.listar_por_usuario(aluno_id)

    def criar_pedido(
        self,
        aluno_id: int,
        lista_id: int,
        itens: Mapping[int, int],
        data_hora: datetime,
    ) -> Pedido:
        aluno = self._obter_aluno(aluno_id)
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
        aluno = self._obter_aluno(aluno_id)
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

    def _obter_aluno(self, aluno_id: int) -> Usuario:
        aluno = self.usuarios.obter_por_id(aluno_id)
        if aluno is None or aluno.papel != PapelUsuario.ALUNO:
            raise AcessoNegadoError("Operação permitida somente para alunos autenticados.")
        return aluno
