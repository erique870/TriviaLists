"""Repositórios em memória para desenvolvimento e testes.

Eles seguem as portas em ``ports.py``; adaptadores SQL futuros só precisam
implementar os mesmos métodos.
"""

from datetime import datetime

from app.domain import ListaDiaria, Pedido, Produto, Restaurante, Usuario, StatusLista


class RepositorioUsuariosEmMemoria:
    def __init__(self, usuarios: list[Usuario] | None = None) -> None:
        self._usuarios = {usuario.id: usuario for usuario in usuarios or []}

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def obter_por_email(self, email: str) -> Usuario | None:
        email_clean = email.strip().lower()
        for u in self._usuarios.values():
            if u.email.strip().lower() == email_clean:
                return u
        return None

    def salvar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None or usuario.id == 0:
            novo_id = max(self._usuarios.keys(), default=0) + 1
            usuario = Usuario(
                id=novo_id,
                nome=usuario.nome,
                email=usuario.email.strip().lower(),
                senha_hash=usuario.senha_hash,
                telefone=usuario.telefone,
                papel=usuario.papel,
                restaurante_id=usuario.restaurante_id,
            )
        self._usuarios[usuario.id] = usuario
        return usuario


class RepositorioRestaurantesEmMemoria:
    def __init__(self, restaurantes: list[Restaurante] | None = None) -> None:
        self._restaurantes = {restaurante.id: restaurante for restaurante in restaurantes or []}

    def obter_por_id(self, restaurante_id: int) -> Restaurante | None:
        return self._restaurantes.get(restaurante_id)

    def listar_ativos(self) -> list[Restaurante]:
        return [r for r in self._restaurantes.values() if r.ativo]

    def salvar(self, restaurante: Restaurante) -> None:
        self._restaurantes[restaurante.id] = restaurante


class RepositorioProdutosEmMemoria:
    def __init__(self, produtos: list[Produto] | None = None) -> None:
        self._produtos = {produto.id: produto for produto in produtos or []}
        self._ultimo_id = max(self._produtos, default=0)

    def proximo_id(self) -> int:
        self._ultimo_id += 1
        return self._ultimo_id

    def obter_por_id(self, produto_id: int) -> Produto | None:
        return self._produtos.get(produto_id)

    def listar_por_restaurante(self, restaurante_id: int) -> list[Produto]:
        return [p for p in self._produtos.values() if p.restaurante_id == restaurante_id]

    def salvar(self, produto: Produto) -> None:
        self._produtos[produto.id] = produto
        self._ultimo_id = max(self._ultimo_id, produto.id)

    def excluir(self, produto_id: int) -> bool:
        return self._produtos.pop(produto_id, None) is not None


class RepositorioListasEmMemoria:
    def __init__(self, listas: list[ListaDiaria] | None = None, produtos=None) -> None:
        self._listas = {lista.id: lista for lista in listas or []}
        self.produtos = produtos

    def proximo_id(self) -> int:
        return max(self._listas, default=0) + 1

    def obter_por_id(self, lista_id: int) -> ListaDiaria | None:
        lista = self._listas.get(lista_id)
        if lista is not None and self.produtos is not None:
            lista.produtos = {pid: self.produtos.obter_por_id(pid) for pid in lista.produtos}
        return lista

    def salvar(self, lista: ListaDiaria) -> None:
        self._listas[lista.id] = lista

    def listar_abertas(self, data_hora: datetime, restaurante_id: int | None = None) -> list[ListaDiaria]:
        return [self.obter_por_id(l.id) for l in self._listas.values()
                if l.status == StatusLista.ABERTA and l.horario_abertura <= data_hora < l.horario_fechamento
                and (restaurante_id is None or l.restaurante_id == restaurante_id)]

    def listar_por_restaurante(self, restaurante_id: int) -> list[ListaDiaria]:
        return sorted([self.obter_por_id(l.id) for l in self._listas.values() if l.restaurante_id == restaurante_id],
                      key=lambda l: (l.data, l.id), reverse=True)

    def listar_expiradas(self, data_hora: datetime) -> list[ListaDiaria]:
        return [self.obter_por_id(l.id) for l in self._listas.values()
                if l.status == StatusLista.ABERTA and l.horario_fechamento <= data_hora]

    def produto_em_uso(self, produto_id: int) -> bool:
        return any(
            produto_id in lista.produtos
            or any(item.produto_id == produto_id for pedido in lista.pedidos for item in pedido.itens)
            for lista in self._listas.values()
        )


class RepositorioPedidosEmMemoria:
    def __init__(self, listas: RepositorioListasEmMemoria) -> None:
        self.listas = listas

    def _todos(self) -> list[Pedido]:
        return [p for l in self.listas._listas.values() for p in l.pedidos]

    def proximo_id(self) -> int:
        return max((p.id for p in self._todos()), default=0) + 1

    def obter_por_id(self, pedido_id: int) -> Pedido | None:
        return next((p for p in self._todos() if p.id == pedido_id), None)

    def listar_por_usuario(self, usuario_id: int) -> list[Pedido]:
        return sorted([p for p in self._todos() if p.usuario_id == usuario_id], key=lambda p: p.id, reverse=True)

    def salvar(self, pedido: Pedido) -> None:
        lista = self.listas.obter_por_id(pedido.lista_diaria_id)
        lista.pedidos = [p for p in lista.pedidos if p.id != pedido.id] + [pedido]

    def salvar_retirada(self, pedido: Pedido) -> None:
        registrado = self.obter_por_id(pedido.id)
        registrado.status_retirada = pedido.status_retirada
