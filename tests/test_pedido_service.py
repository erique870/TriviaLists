from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.application import ServicoPedido
from app.application.repositories import (
    RepositorioListasEmMemoria,
    RepositorioPedidosEmMemoria,
    RepositorioUsuariosEmMemoria,
)
from app.domain import (
    ListaDiaria,
    PapelUsuario,
    Produto,
    StatusPedido,
    Usuario,
    ValidacaoDeDominioError,
)

UTC = timezone.utc


def contexto_pedidos():
    aluno = Usuario(1, "Aluno", "aluno@example.com", "hash", "11999990000", PapelUsuario.ALUNO)
    produto = Produto(10, 20, "Almoço", Decimal("25.50"))
    lista = ListaDiaria(
        id=30,
        restaurante_id=20,
        data=date(2026, 10, 30),
        horario_abertura=datetime(2026, 10, 30, 8, tzinfo=UTC),
        horario_fechamento=datetime(2026, 10, 30, 11, tzinfo=UTC),
        produtos={produto.id: produto},
    )
    listas = RepositorioListasEmMemoria([lista])
    pedidos = RepositorioPedidosEmMemoria()
    service = ServicoPedido(
        RepositorioUsuariosEmMemoria([aluno]), listas, pedidos
    )
    return service, lista, pedidos


def test_cria_e_cancela_pedido_persistindo_o_estado():
    service, lista, pedidos = contexto_pedidos()
    criado = service.criar_pedido(
        aluno_id=1,
        lista_id=30,
        itens={10: 2},
        data_hora=datetime(2026, 10, 30, 9, tzinfo=UTC),
    )

    assert criado.valor_total == Decimal("51.00")
    assert pedidos.obter_por_id(criado.id) is criado

    cancelado = service.cancelar_pedido(
        aluno_id=1,
        pedido_id=criado.id,
        data_hora=datetime(2026, 10, 30, 9, 5, tzinfo=UTC),
    )

    assert cancelado.status == StatusPedido.CANCELADO
    assert lista.pedidos[0].status == StatusPedido.CANCELADO


def test_lista_fechada_nao_aceita_novo_pedido():
    service, lista, _ = contexto_pedidos()
    lista.fechar_lista()

    with pytest.raises(ValidacaoDeDominioError, match="lista fechada"):
        service.criar_pedido(
            aluno_id=1,
            lista_id=30,
            itens={10: 1},
            data_hora=datetime(2026, 10, 30, 9, tzinfo=UTC),
        )
