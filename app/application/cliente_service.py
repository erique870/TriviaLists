"""CU01, CU02 e CU03: operações do cliente com persistência transacional."""

from app.core.clock import agora
from app.domain import AcessoNegadoError, PapelUsuario, ValidacaoDeDominioError


class ServicoCliente:
    def __init__(self, contexto, relogio=agora):
        self.contexto = contexto
        self.relogio = relogio

    def _cliente(self, usuario_id):
        cliente = self.contexto.usuarios.obter_por_id(usuario_id)
        if cliente is None or cliente.papel != PapelUsuario.CLIENTE:
            raise AcessoNegadoError("Somente clientes podem realizar esta operação.")
        return cliente

    def listar_abertas(self, usuario_id, restaurante_id=None):
        self._cliente(usuario_id)
        return self.contexto.listas.listar_abertas(self.relogio(), restaurante_id)

    def criar_pedido(self, usuario_id, lista_id, itens):
        with self.contexto.transacao():
            cliente = self._cliente(usuario_id)
            lista = self.contexto.listas.obter_por_id(lista_id)
            if lista is None:
                raise ValidacaoDeDominioError("Lista diária não encontrada.", codigo="lista_nao_encontrada")
            # O identificador é reservado antes da mutação do agregado em memória.
            pedido_id = self.contexto.pedidos.proximo_id()
            pedido = lista.criar_pedido(cliente, itens, self.relogio(), pedido_id)
            self.contexto.pedidos.salvar(pedido)
            return pedido

    def meus_pedidos(self, usuario_id):
        self._cliente(usuario_id)
        return self.contexto.pedidos.listar_por_usuario(usuario_id)

    def cancelar_pedido(self, usuario_id, pedido_id):
        with self.contexto.transacao():
            cliente = self._cliente(usuario_id)
            pedido = self.contexto.pedidos.obter_por_id(pedido_id)
            if pedido is None or pedido.usuario_id != cliente.id:
                raise AcessoNegadoError("Pedido indisponível para este usuário.")
            lista = self.contexto.listas.obter_por_id(pedido.lista_diaria_id)
            lista.cancelar_pedido(cliente, pedido_id, self.relogio())
            pedido = next(p for p in lista.pedidos if p.id == pedido_id)
            self.contexto.pedidos.salvar(pedido)
            return pedido
