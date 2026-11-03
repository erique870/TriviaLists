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
    outro_aluno = Usuario(2, "Outra", "outra@example.com", "hash", "11888880000", PapelUsuario.ALUNO)
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
        RepositorioUsuariosEmMemoria([aluno, outro_aluno]), listas, pedidos
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


def test_lista_fechada_nao_aceita_cancelamento():
    service, lista, _ = contexto_pedidos()
    criado = service.criar_pedido(
        1, lista.id, {10: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC)
    )
    lista.fechar_lista()

    with pytest.raises(ValidacaoDeDominioError, match="lista fechada"):
        service.cancelar_pedido(
            1, criado.id, datetime(2026, 10, 30, 9, 30, tzinfo=UTC)
        )


def test_cu01_lista_abertas_filtra_status_prazo_e_restaurante():
    service, lista_aberta, _ = contexto_pedidos()
    lista_expirada = ListaDiaria(
        id=31,
        restaurante_id=20,
        data=date(2026, 10, 30),
        horario_abertura=datetime(2026, 10, 30, 8, tzinfo=UTC),
        horario_fechamento=datetime(2026, 10, 30, 10, tzinfo=UTC),
    )
    lista_fechada = ListaDiaria(
        id=32,
        restaurante_id=20,
        data=date(2026, 10, 30),
        horario_abertura=datetime(2026, 10, 30, 8, tzinfo=UTC),
        horario_fechamento=datetime(2026, 10, 30, 12, tzinfo=UTC),
    )
    lista_fechada.fechar_lista()
    lista_outro_restaurante = ListaDiaria(
        id=33,
        restaurante_id=21,
        data=date(2026, 10, 30),
        horario_abertura=datetime(2026, 10, 30, 8, tzinfo=UTC),
        horario_fechamento=datetime(2026, 10, 30, 12, tzinfo=UTC),
    )
    lista_ainda_nao_aberta = ListaDiaria(
        id=34,
        restaurante_id=20,
        data=date(2026, 10, 30),
        horario_abertura=datetime(2026, 10, 30, 11, tzinfo=UTC),
        horario_fechamento=datetime(2026, 10, 30, 12, tzinfo=UTC),
    )
    service.listas.salvar(lista_expirada)
    service.listas.salvar(lista_fechada)
    service.listas.salvar(lista_outro_restaurante)
    service.listas.salvar(lista_ainda_nao_aberta)
    agora = datetime(2026, 10, 30, 10, 30, tzinfo=UTC)

    assert service.listar_listas_abertas(1, agora) == [lista_aberta, lista_outro_restaurante]
    assert service.listar_listas_abertas(1, agora, restaurante_id=20) == [lista_aberta]
    assert service.listar_listas_abertas(1, agora, restaurante_id=999) == []


def test_listar_meus_pedidos_nao_expoe_pedidos_de_outro_aluno():
    service, _, _ = contexto_pedidos()
    pedido_aluno_1 = service.criar_pedido(
        1, 30, {10: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC)
    )
    pedido_aluno_2 = service.criar_pedido(
        2, 30, {10: 2}, datetime(2026, 10, 30, 9, 5, tzinfo=UTC)
    )

    assert service.listar_meus_pedidos(1) == [pedido_aluno_1]
    assert service.listar_meus_pedidos(2) == [pedido_aluno_2]
