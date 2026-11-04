"""Implementação dos casos de uso CU04 a CU07 (mundo restaurante)."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal

from app.application.ports import (
    RepositorioListaDiaria,
    RepositorioProduto,
    RepositorioRestaurante,
    RepositorioUsuario,
    RepositorioPedido,
)
from app.core.clock import agora
from app.domain import (
    AcessoNegadoError,
    ListaDiaria,
    PapelUsuario,
    Produto,
    StatusLista,
    Usuario,
    ValidacaoDeDominioError,
    StatusPedido,
    RegraDeNegocioError,
    Pedido,
    StatusRetirada,
)


class ServicoRestaurante:
    """Orquestra operações do parceiro sem conhecer transporte ou persistência."""

    def __init__(
        self,
        usuarios: RepositorioUsuario,
        restaurantes: RepositorioRestaurante,
        produtos: RepositorioProduto,
        listas: RepositorioListaDiaria,
        transacao=nullcontext,
        notificacoes=None,
        pedidos: RepositorioPedido | None = None,
    ) -> None:
        self.usuarios = usuarios
        self.restaurantes = restaurantes
        self.produtos = produtos
        self.listas = listas
        self.transacao = transacao
        self.notificacoes = notificacoes
        self.pedidos = pedidos

    def criar_lista_diaria(
        self,
        parceiro_id: int,
        dia: date,
        produto_ids: list[int],
        publicada_em: datetime,
        horario_abertura: time | None = None,
        horario_fechamento: time | None = None,
    ) -> ListaDiaria:
        """CU04: publica o cardápio usando apenas o restaurante da sessão."""
        with self.transacao():
            _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
            produtos = self._produtos_do_restaurante(restaurante_id, produto_ids)
            restaurante = self._obter_restaurante(restaurante_id)
            lista = restaurante.criar_lista_diaria(
                lista_id=self.listas.proximo_id(), dia=dia, produtos=produtos,
                publicada_em=publicada_em, horario_abertura=horario_abertura,
                horario_fechamento=horario_fechamento,
            )
            self.listas.salvar(lista)
            if self.notificacoes is not None:
                self.notificacoes.agendar(lista.id)
        return lista

    def abrir_lista(self, parceiro_id: int, lista_id: int, data_hora: datetime | None = None) -> ListaDiaria:
        """CU05: abre uma lista que pertence ao restaurante autenticado."""
        with self.transacao():
            lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
            if not lista.validar_horario_fechamento(data_hora or agora()):
                raise ValidacaoDeDominioError("Uma lista vencida não pode ser reaberta.", codigo="fechamento_no_passado")
            lista.abrir_lista()
            self.listas.salvar(lista)
        return lista

    def fechar_lista(self, parceiro_id: int, lista_id: int) -> ListaDiaria:
        """CU05: fecha uma lista; o relatório pode ser consultado em seguida."""
        with self.transacao():
            lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
            lista.fechar_lista()
            self.listas.salvar(lista)
            self.gerar_relatorio_de_producao(parceiro_id, lista_id)
        return lista

    def gerar_relatorio_de_producao(
        self, parceiro_id: int, lista_id: int
    ) -> list[dict[str, int | str]]:
        """CU06: consolida apenas após o encerramento da lista."""
        lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
        if lista.status != StatusLista.FECHADA:
            raise ValidacaoDeDominioError(
                "A lista deve estar fechada para gerar o relatório.",
                codigo="lista_ainda_aberta",
            )
        return lista.gerar_relatorio_de_producao()

    def obter_relatorio(self, parceiro_id: int, lista_id: int) -> dict:
        with self.transacao():
            itens = self.gerar_relatorio_de_producao(parceiro_id, lista_id)
            lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
            return self.relatorio(lista, itens)

    @staticmethod
    def relatorio(lista: ListaDiaria, itens=None) -> dict:
        ativos = [p for p in lista.pedidos if p.status == StatusPedido.ATIVO]
        return {
            "lista_id": lista.id, "data": lista.data,
            "itens": lista.gerar_relatorio_de_producao() if itens is None else itens,
            "total_pedidos": len(ativos),
            "valor_total": sum((p.valor_total for p in ativos), Decimal("0.00")),
            "mensagem": "Lista encerrada sem pedidos registrados para a data" if not ativos else None,
        }

    def listar_listas(self, parceiro_id: int) -> list[ListaDiaria]:
        _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
        return self.listas.listar_por_restaurante(restaurante_id)

    def listar_pedidos(self, parceiro_id: int, lista_id: int) -> list[Pedido]:
        """Consulta os pedidos, inclusive cancelados, da lista do próprio parceiro."""
        lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
        return sorted(lista.pedidos, key=lambda pedido: pedido.id)

    def confirmar_retirada(self, parceiro_id: int, lista_id: int, pedido_id: int) -> Pedido:
        """Conclui a entrega sob o mesmo bloqueio usado pelo cancelamento."""
        with self.transacao():
            lista = self._obter_lista_do_parceiro(parceiro_id, lista_id)
            pedido = next((p for p in lista.pedidos if p.id == pedido_id), None)
            if pedido is None:
                raise ValidacaoDeDominioError("Pedido não encontrado nesta lista.", codigo="pedido_nao_encontrado")
            # Repetir a confirmação é seguro, por exemplo após uma falha de rede.
            if pedido.status == StatusPedido.ATIVO and pedido.status_retirada == StatusRetirada.RETIRADO:
                return pedido
            pedido.confirmar_retirada()
            assert self.pedidos is not None, "Repositório de pedidos não configurado."
            self.pedidos.salvar_retirada(pedido)
            return pedido

    def obter_restaurante(self, parceiro_id: int):
        _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
        return self._obter_restaurante(restaurante_id)

    def configurar_horarios(self, parceiro_id: int, abertura: time, fechamento: time):
        if fechamento <= abertura:
            raise ValidacaoDeDominioError("Fechamento deve ocorrer após a abertura.")
        with self.transacao():
            restaurante = self.obter_restaurante(parceiro_id)
            restaurante.horario_padrao_abertura = abertura
            restaurante.horario_padrao_fechamento = fechamento
            self.restaurantes.salvar(restaurante)
            return restaurante

    def encerrar_expiradas(self, data_hora: datetime) -> list[dict]:
        with self.transacao():
            relatorios = []
            for lista in self.listas.listar_expiradas(data_hora):
                lista.fechar_lista()
                self.listas.salvar(lista)
                relatorios.append(self.relatorio(lista))
            return relatorios

    def cadastrar_produto(
        self,
        parceiro_id: int,
        nome: str,
        preco: Decimal,
        descricao: str = "",
        disponivel: bool = True,
    ) -> Produto:
        """CU07: cadastra um item no catálogo do próprio restaurante."""
        with self.transacao():
            _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
            produto = Produto(
                id=self.produtos.proximo_id(),
                restaurante_id=restaurante_id,
                nome=nome,
                preco=preco,
                descricao=descricao,
                disponivel=disponivel,
            )
            self.produtos.salvar(produto)
            return produto

    def atualizar_produto(
        self,
        parceiro_id: int,
        produto_id: int,
        *,
        nome: str | None = None,
        preco: Decimal | None = None,
        descricao: str | None = None,
        disponivel: bool | None = None,
    ) -> Produto:
        """CU07: atualiza ou altera disponibilidade sem trocar a propriedade."""
        with self.transacao():
            _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
            produto = self._obter_produto_do_restaurante(produto_id, restaurante_id)
            atualizado = replace(
                produto,
                nome=produto.nome if nome is None else nome,
                preco=produto.preco if preco is None else preco,
                descricao=produto.descricao if descricao is None else descricao,
                disponivel=produto.disponivel if disponivel is None else disponivel,
            )
            self.produtos.salvar(atualizado)
            return atualizado

    def listar_produtos(self, parceiro_id: int) -> list[Produto]:
        """CU07: lista o catálogo do restaurante da sessão."""
        _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
        return self.produtos.listar_por_restaurante(restaurante_id)

    def excluir_produto(self, parceiro_id: int, produto_id: int) -> None:
        """CU07: exclui somente produtos próprios sem vínculos históricos."""
        with self.transacao():
            _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
            self._obter_produto_do_restaurante(produto_id, restaurante_id)
            # O produto fica bloqueado até o commit, assim como na publicação.
            # A consulta inclui pedidos cancelados e listas já encerradas.
            if self.listas.produto_em_uso(produto_id) or not self.produtos.excluir(produto_id):
                raise RegraDeNegocioError(
                    "Este produto está vinculado a listas ou pedidos e não pode ser excluído. "
                    "Use Desativar para impedir novos pedidos e preservar o histórico.",
                    codigo="produto_em_uso",
                )

    def _obter_parceiro_e_restaurante(self, parceiro_id: int) -> tuple[Usuario, int]:
        parceiro = self.usuarios.obter_por_id(parceiro_id)
        if parceiro is None or parceiro.papel != PapelUsuario.PARCEIRO:
            raise AcessoNegadoError("Somente parceiros podem realizar esta operação.")
        # A própria entidade garante que parceiro possui restaurante_id.
        assert parceiro.restaurante_id is not None
        return parceiro, parceiro.restaurante_id

    def _obter_restaurante(self, restaurante_id: int):
        restaurante = self.restaurantes.obter_por_id(restaurante_id)
        if restaurante is None:
            raise ValidacaoDeDominioError("Restaurante não encontrado.", codigo="restaurante_nao_encontrado")
        return restaurante

    def _obter_lista_do_parceiro(self, parceiro_id: int, lista_id: int) -> ListaDiaria:
        _, restaurante_id = self._obter_parceiro_e_restaurante(parceiro_id)
        lista = self.listas.obter_por_id(lista_id)
        if lista is None:
            raise ValidacaoDeDominioError("Lista diária não encontrada.", codigo="lista_nao_encontrada")
        if lista.restaurante_id != restaurante_id:
            raise AcessoNegadoError("Lista não pertence ao restaurante do parceiro.")
        return lista

    def _obter_produto_do_restaurante(self, produto_id: int, restaurante_id: int) -> Produto:
        produto = self.produtos.obter_por_id(produto_id)
        if produto is None:
            raise ValidacaoDeDominioError("Produto não encontrado.", codigo="produto_nao_encontrado")
        if produto.restaurante_id != restaurante_id:
            raise AcessoNegadoError("Produto não pertence ao restaurante do parceiro.")
        return produto

    def _produtos_do_restaurante(
        self, restaurante_id: int, produto_ids: list[int]
    ) -> list[Produto]:
        if not produto_ids:
            raise ValidacaoDeDominioError(
                "A lista diária precisa conter ao menos um produto.",
                codigo="lista_sem_produtos",
            )
        if len(set(produto_ids)) != len(produto_ids):
            raise ValidacaoDeDominioError(
                "Um produto não pode ser informado mais de uma vez na lista.",
                codigo="produto_duplicado_na_lista",
            )
        return [self._obter_produto_do_restaurante(produto_id, restaurante_id) for produto_id in sorted(produto_ids)]
