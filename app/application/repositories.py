"""Repositórios em memória para desenvolvimento e testes.

Eles seguem as portas em ``ports.py``; adaptadores SQL futuros só precisam
implementar os mesmos métodos.
"""

from app.domain import ListaDiaria, Produto, Restaurante, Usuario


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
