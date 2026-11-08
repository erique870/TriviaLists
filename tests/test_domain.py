from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.domain import (
    AcessoNegadoError,
    HorarioLimiteExcedidoError,
    PedidoAtivoExistenteError,
    PapelUsuario,
    RegraDeNegocioError,
    Restaurante,
    StatusPedido,
    StatusRetirada,
    TipoCardapio,
    Usuario,
    ValidacaoDeDominioError,
)

UTC = timezone.utc
DIA = date(2026, 10, 30)


def usuario_aluno(usuario_id: int = 1) -> Usuario:
    return Usuario(
        id=usuario_id,
        nome=f"Aluno {usuario_id}",
        email=f"aluno{usuario_id}@exemplo.com",
        senha_hash="hash-seguro",
        telefone="11999990000",
        papel=PapelUsuario.ALUNO,
    )


def restaurante(tipo: TipoCardapio = TipoCardapio.FIXO) -> Restaurante:
    return Restaurante(
        id=10,
        nome="Salsalito",
        endereco="Campus",
        horario_padrao_abertura=time(8),
        horario_padrao_fechamento=time(11),
        tipo_cardapio=tipo,
    )


def produto(preco: str = "25.50"):
    from app.domain import Produto

    return Produto(
        id=100,
        restaurante_id=10,
        nome="Quentinha",
        preco=Decimal(preco),
    )


def publicar(
    tipo: TipoCardapio = TipoCardapio.FIXO,
    quando: datetime = datetime(2026, 10, 30, 8, tzinfo=UTC),
):
    return restaurante(tipo).criar_lista_diaria(20, DIA, [produto()], quando)


def test_pedido_e_aceito_antes_do_horario_limite():
    lista = publicar()

    pedido = lista.criar_pedido(
        usuario_aluno(), {100: 2}, datetime(2026, 10, 30, 10, 59, tzinfo=UTC), 1
    )

    assert pedido.valor_total == Decimal("51.00")
    assert pedido.itens[0].preco_unitario == Decimal("25.50")


@pytest.mark.parametrize("hora", [(11, 0), (11, 1)])
def test_pedido_na_hora_limite_ou_depois_e_rejeitado(hora):
    lista = publicar()

    with pytest.raises(RegraDeNegocioError, match="horário limite"):
        lista.criar_pedido(
            usuario_aluno(),
            {100: 1},
            datetime(2026, 10, 30, *hora, tzinfo=UTC),
            1,
        )


def test_erro_de_horario_informa_codigo_regra_e_mensagem_customizavel():
    erro = HorarioLimiteExcedidoError("Prazo personalizado encerrado.")

    assert erro.codigo == "horario_limite_excedido"
    assert erro.regras == ("RN01", "RN04")
    assert erro.to_dict() == {
        "codigo": "horario_limite_excedido",
        "mensagem": "Prazo personalizado encerrado.",
        "regras": ["RN01", "RN04"],
    }


def test_cardapio_variavel_publicado_tarde_estende_corte_por_trinta_minutos():
    lista = publicar(
        TipoCardapio.VARIAVEL,
        datetime(2026, 10, 30, 11, 10, tzinfo=UTC),
    )

    pedido = lista.criar_pedido(
        usuario_aluno(), {100: 1}, datetime(2026, 10, 30, 11, 39, tzinfo=UTC), 1
    )

    assert pedido.status == StatusPedido.ATIVO
    assert lista.horario_fechamento == datetime(2026, 10, 30, 11, 40, tzinfo=UTC)
    with pytest.raises(RegraDeNegocioError, match="horário limite"):
        lista.criar_pedido(
            usuario_aluno(2),
            {100: 1},
            datetime(2026, 10, 30, 11, 40, tzinfo=UTC),
            2,
        )


def test_cardapio_fixo_nao_recebe_extensao_ao_ser_publicado_tarde():
    with pytest.raises(ValidacaoDeDominioError, match="ultrapassado"):
        publicar(
            TipoCardapio.FIXO,
            datetime(2026, 10, 30, 11, 10, tzinfo=UTC),
        )


def test_lista_fechada_manualmente_impede_pedido_e_cancelamento():
    lista = publicar()
    aluno = usuario_aluno()
    lista.criar_pedido(aluno, {100: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1)
    lista.fechar_lista()
    with pytest.raises(RegraDeNegocioError, match="fechada"):
        lista.criar_pedido(usuario_aluno(2), {100: 1}, datetime(2026, 10, 30, 9, 1, tzinfo=UTC), 2)
    with pytest.raises(RegraDeNegocioError, match="fechada"):
        lista.cancelar_pedido(aluno, 1, datetime(2026, 10, 30, 9, 1, tzinfo=UTC))


def test_lista_ainda_nao_aberta_impede_pedido():
    lista = publicar()
    with pytest.raises(RegraDeNegocioError, match="ainda não abriu"):
        lista.criar_pedido(usuario_aluno(), {100: 1}, datetime(2026, 10, 30, 7, tzinfo=UTC), 1)


def test_um_pedido_ativo_por_aluno_e_lista_cancelamento_libera_novo_pedido():
    lista = publicar()
    aluno = usuario_aluno()
    lista.criar_pedido(aluno, {100: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1)

    with pytest.raises(PedidoAtivoExistenteError, match="pedido ativo") as erro:
        lista.criar_pedido(
            aluno, {100: 1}, datetime(2026, 10, 30, 9, 1, tzinfo=UTC), 2
        )
    assert erro.value.codigo == "pedido_ativo_existente"
    assert erro.value.regras == ("RN03",)

    lista.cancelar_pedido(aluno, 1, datetime(2026, 10, 30, 9, 2, tzinfo=UTC))
    novo = lista.criar_pedido(
        aluno, {100: 2}, datetime(2026, 10, 30, 9, 3, tzinfo=UTC), 2
    )
    assert novo.status == StatusPedido.ATIVO


def test_relatorio_soma_somente_pedidos_ativos_e_preco_fica_registrado():
    lista = publicar()
    aluno = usuario_aluno()
    pedido = lista.criar_pedido(
        aluno, {100: 2}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1
    )
    lista.cancelar_pedido(aluno, 1, datetime(2026, 10, 30, 9, 1, tzinfo=UTC))
    lista.criar_pedido(
        usuario_aluno(2), {100: 3}, datetime(2026, 10, 30, 9, 2, tzinfo=UTC), 2
    )
    lista.produtos[100].preco = Decimal("30.00")

    assert pedido.valor_total == Decimal("51.00")
    assert lista.gerar_relatorio_de_producao() == [
        {"produto_id": 100, "produto": "Quentinha", "quantidade": 3}
    ]


def test_aluno_nao_pode_cancelar_pedido_de_outra_pessoa():
    lista = publicar()
    lista.criar_pedido(
        usuario_aluno(), {100: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1
    )

    with pytest.raises(AcessoNegadoError, match="indisponível") as erro:
        lista.cancelar_pedido(
            usuario_aluno(2), 1, datetime(2026, 10, 30, 9, 1, tzinfo=UTC)
        )
    assert erro.value.codigo == "acesso_negado"
    assert erro.value.regras == ("RN05",)


def test_pedido_nao_aceita_produto_de_fora_do_cardapio():
    lista = publicar()

    with pytest.raises(ValidacaoDeDominioError, match="não pertence ao cardápio"):
        lista.criar_pedido(
            usuario_aluno(), {999: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1
        )


def test_pedido_confirma_retirada():
    lista = publicar()
    pedido = lista.criar_pedido(
        usuario_aluno(), {100: 1}, datetime(2026, 10, 30, 9, tzinfo=UTC), 1
    )

    pedido.confirmar_retirada()

    assert pedido.status_retirada == StatusRetirada.RETIRADO
