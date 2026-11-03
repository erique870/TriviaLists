"""Repositórios em memória para testes; seguem as portas em ``ports.py``."""

from app.domain import ListaDiaria, Pedido, Produto, Restaurante, Usuario


class RepositorioUsuariosEmMemoria:
    def __init__(self, usuarios: list[Usuario] | None = None) -> None:
        self._usuarios = {usuario.id: usuario for usuario in usuarios or []}

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)


class RepositorioRestaurantesEmMemoria:
    def __init__(self, restaurantes: list[Restaurante] | None = None) -> None:
        self._restaurantes = {restaurante.id: restaurante for restaurante in restaurantes or []}

    def obter_por_id(self, restaurante_id: int) -> Restaurante | None:
        return self._restaurantes.get(restaurante_id)

    def salvar(self, restaurante: Restaurante) -> None:
        self._restaurantes[restaurante.id] = restaurante


class RepositorioProdutosEmMemoria:
    def __init__(self, produtos: list[Produto] | None = None) -> None:
        self._produtos = {produto.id: produto for produto in produtos or []}

    def proximo_id(self) -> int:
        return max(self._produtos, default=0) + 1

    def obter_por_id(self, produto_id: int) -> Produto | None:
        return self._produtos.get(produto_id)

    def listar_por_restaurante(self, restaurante_id: int) -> list[Produto]:
        return [p for p in self._produtos.values() if p.restaurante_id == restaurante_id]

    def salvar(self, produto: Produto) -> None:
        self._produtos[produto.id] = produto


class RepositorioListasEmMemoria:
    def __init__(self, listas: list[ListaDiaria] | None = None) -> None:
        self._listas = {lista.id: lista for lista in listas or []}

    def proximo_id(self) -> int:
        return max(self._listas, default=0) + 1

    def obter_por_id(self, lista_id: int) -> ListaDiaria | None:
        return self._listas.get(lista_id)

    def salvar(self, lista: ListaDiaria) -> None:
        self._listas[lista.id] = lista


class RepositorioPedidosEmMemoria:
    def __init__(self, pedidos: list[Pedido] | None = None) -> None:
        self._pedidos = {pedido.id: pedido for pedido in pedidos or []}

    def proximo_id(self) -> int:
        return max(self._pedidos, default=0) + 1

    def obter_por_id(self, pedido_id: int) -> Pedido | None:
        return self._pedidos.get(pedido_id)

    def salvar(self, pedido: Pedido) -> None:
        self._pedidos[pedido.id] = pedido
