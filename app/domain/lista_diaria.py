from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Mapping

from app.domain.enums import PapelUsuario, StatusLista, StatusPedido, StatusRetirada
from app.domain.exceptions import (
    AcessoNegadoError,
    HorarioLimiteExcedidoError,
    PedidoAtivoExistenteError,
    RegraDeNegocioError,
    ValidacaoDeDominioError,
)
from app.domain.item_pedido import ItemPedido
from app.domain.pedido import Pedido
from app.domain.produto import Produto
from app.domain.usuario import Usuario


@dataclass(slots=True)
class ListaDiaria:
    id: int
    restaurante_id: int
    data: date
    horario_abertura: datetime
    horario_fechamento: datetime
    status: StatusLista = StatusLista.ABERTA
    produtos: dict[int, Produto] = field(default_factory=dict)
    pedidos: list[Pedido] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.horario_fechamento <= self.horario_abertura:
            raise ValidacaoDeDominioError("Fechamento deve ocorrer após a abertura.")

    def abrir_lista(self) -> None:
        self.status = StatusLista.ABERTA

    def validar_recebimento(self, data_hora: datetime) -> None:
        if self.status != StatusLista.ABERTA:
            raise RegraDeNegocioError("A lista deste restaurante está fechada.", codigo="lista_fechada", regras=("RN01",))
        if not self.validar_horario_fechamento(data_hora):
            raise HorarioLimiteExcedidoError()
        if data_hora < self.horario_abertura:
            raise RegraDeNegocioError("A lista ainda não abriu para pedidos.", codigo="lista_ainda_nao_aberta", regras=("RN01",))

    def fechar_lista(self) -> None:
        self.status = StatusLista.FECHADA

    def validar_horario_fechamento(self, data_hora: datetime) -> bool:
        """RN01/RN04: aceita operações somente antes do horário limite."""
        if (data_hora.utcoffset() is None) != (
            self.horario_fechamento.utcoffset() is None
        ):
            raise ValidacaoDeDominioError(
                "Não é possível comparar horário com fuso e horário sem fuso."
            )
        return data_hora < self.horario_fechamento

    def possui_pedido_ativo(self, usuario_id: int) -> bool:
        return any(
            pedido.usuario_id == usuario_id and pedido.status == StatusPedido.ATIVO
            for pedido in self.pedidos
        )

    def vincular_produtos(self, produtos: list[Produto]) -> None:
        for produto in produtos:
            if produto.restaurante_id != self.restaurante_id:
                raise AcessoNegadoError("Produto não pertence ao restaurante desta lista.")
            if not produto.disponivel:
                raise ValidacaoDeDominioError(f"Produto indisponível: {produto.nome}.")
        self.produtos.update({produto.id: produto for produto in produtos})

    def criar_pedido(
        self,
        usuario: Usuario,
        itens: Mapping[int, int],
        data_hora: datetime,
        pedido_id: int,
    ) -> Pedido:
        if usuario.papel != PapelUsuario.ALUNO:
            raise AcessoNegadoError("Somente alunos podem criar pedidos.")
        self.validar_recebimento(data_hora)
        if self.possui_pedido_ativo(usuario.id):
            raise PedidoAtivoExistenteError()
        if not itens:
            raise ValidacaoDeDominioError(
                "Pedido precisa conter ao menos um produto.",
                codigo="pedido_sem_itens",
            )

        itens_pedido: list[ItemPedido] = []
        for produto_id, quantidade in itens.items():
            produto = self.produtos.get(produto_id)
            if produto is None:
                raise ValidacaoDeDominioError(
                    "Produto não pertence ao cardápio desta lista.",
                    codigo="produto_fora_do_cardapio",
                )
            if not produto.disponivel:
                raise ValidacaoDeDominioError(
                    f"Produto indisponível: {produto.nome}.",
                    codigo="produto_indisponivel",
                )
            itens_pedido.append(
                ItemPedido(
                    produto_id=produto.id,
                    quantidade=quantidade,
                    preco_unitario=produto.obter_preco(),
                )
            )

        pedido = Pedido(
            id=pedido_id,
            lista_diaria_id=self.id,
            usuario_id=usuario.id,
            data_hora_pedido=data_hora,
            itens=itens_pedido,
        )
        self.pedidos.append(pedido)
        return pedido

    def cancelar_pedido(self, usuario: Usuario, pedido_id: int, data_hora: datetime) -> None:
        if usuario.papel != PapelUsuario.ALUNO:
            raise AcessoNegadoError("Somente alunos podem cancelar pedidos.")
        self.validar_recebimento(data_hora)
        pedido = next((p for p in self.pedidos if p.id == pedido_id), None)
        if pedido is None or pedido.usuario_id != usuario.id:
            raise AcessoNegadoError("Pedido indisponível para este usuário.")
        if pedido.status != StatusPedido.ATIVO:
            raise RegraDeNegocioError(
                "Este pedido já está cancelado.", codigo="pedido_ja_cancelado"
            )
        if pedido.status_retirada == StatusRetirada.RETIRADO:
            raise RegraDeNegocioError(
                "Um pedido já retirado não pode ser cancelado.", codigo="pedido_ja_retirado"
            )
        pedido.status = StatusPedido.CANCELADO

    def gerar_relatorio_de_producao(self) -> list[dict[str, int | str]]:
        totais: dict[int, dict[str, int | str]] = {}
        for pedido in self.pedidos:
            if pedido.status != StatusPedido.ATIVO:
                continue
            for item in pedido.itens:
                produto = self.produtos[item.produto_id]
                linha = totais.setdefault(
                    produto.id,
                    {"produto_id": produto.id, "produto": produto.nome, "quantidade": 0},
                )
                linha["quantidade"] = int(linha["quantidade"]) + item.quantidade
        return [totais[produto_id] for produto_id in sorted(totais)]
