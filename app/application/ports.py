"""Portas de persistência usadas pelos casos de uso.

As implementações concretas podem ser em memória (testes) ou em um banco de
dados. O domínio e os serviços não dependem dessa escolha.
"""

from __future__ import annotations

from typing import Protocol

from app.domain import ListaDiaria, Pedido, Produto, Restaurante, Usuario


class RepositorioUsuario(Protocol):
    def obter_por_id(self, usuario_id: int) -> Usuario | None: ...


class RepositorioRestaurante(Protocol):
    def obter_por_id(self, restaurante_id: int) -> Restaurante | None: ...

    def salvar(self, restaurante: Restaurante) -> None: ...


class RepositorioProduto(Protocol):
    def proximo_id(self) -> int: ...

    def obter_por_id(self, produto_id: int) -> Produto | None: ...

    def listar_por_restaurante(self, restaurante_id: int) -> list[Produto]: ...

    def salvar(self, produto: Produto) -> None: ...


class RepositorioListaDiaria(Protocol):
    def proximo_id(self) -> int: ...

    def obter_por_id(self, lista_id: int) -> ListaDiaria | None: ...

    def salvar(self, lista: ListaDiaria) -> None: ...


class RepositorioPedido(Protocol):
    def proximo_id(self) -> int: ...

    def obter_por_id(self, pedido_id: int) -> Pedido | None: ...

    def salvar(self, pedido: Pedido) -> None: ...
