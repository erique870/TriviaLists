from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.application import ServicoRestaurante
from app.application.repositories import (
    RepositorioListasEmMemoria,
    RepositorioProdutosEmMemoria,
    RepositorioRestaurantesEmMemoria,
    RepositorioUsuariosEmMemoria,
)
from app.domain import (
    AcessoNegadoError,
    PapelUsuario,
    Restaurante,
    StatusLista,
    TipoCardapio,
    Usuario,
    ValidacaoDeDominioError,
)

UTC = timezone.utc


@pytest.fixture
def contexto():
    restaurante = Restaurante(
        id=10,
        nome="Salsalito",
        endereco="Campus",
        horario_padrao_abertura=time(8),
        horario_padrao_fechamento=time(11),
        tipo_cardapio=TipoCardapio.VARIAVEL,
    )
    outro_restaurante = Restaurante(
        id=20,
        nome="Pilograma",
        endereco="Campus",
        horario_padrao_abertura=time(8),
        horario_padrao_fechamento=time(11),
        tipo_cardapio=TipoCardapio.FIXO,
    )
    parceiro = Usuario(1, "Parceiro", "p@exemplo.com", "hash", "119", PapelUsuario.PARCEIRO, 10)
    outro_parceiro = Usuario(2, "Outro", "o@exemplo.com", "hash", "118", PapelUsuario.PARCEIRO, 20)
    cliente = Usuario(3, "Cliente", "a@exemplo.com", "hash", "117", PapelUsuario.CLIENTE)
    return ServicoRestaurante(
        RepositorioUsuariosEmMemoria([parceiro, outro_parceiro, cliente]),
        RepositorioRestaurantesEmMemoria([restaurante, outro_restaurante]),
        RepositorioProdutosEmMemoria(),
        RepositorioListasEmMemoria(),
    )


def test_cu07_cadastra_atualiza_e_lista_apenas_produtos_do_parceiro(contexto):
    produto = contexto.cadastrar_produto(1, "Quentinha", Decimal("25.50"), "Frango")
    outro = contexto.cadastrar_produto(2, "Tapioca", Decimal("12"))

    atualizado = contexto.atualizar_produto(1, produto.id, preco=Decimal("27"), disponivel=False)

    assert atualizado.preco == Decimal("27")
    assert not atualizado.disponivel
    assert contexto.listar_produtos(1) == [atualizado]
    assert contexto.listar_produtos(2) == [outro]


def test_cu04_cria_lista_usando_restaurante_da_sessao_e_aplica_rn02(contexto):
    produto = contexto.cadastrar_produto(1, "Quentinha", Decimal("25.50"))

    lista = contexto.criar_lista_diaria(
        1, date(2026, 10, 30), [produto.id], datetime(2026, 10, 30, 11, 10, tzinfo=UTC)
    )

    assert lista.restaurante_id == 10
    assert lista.produtos == {produto.id: produto}
    assert lista.horario_fechamento == datetime(2026, 10, 30, 11, 40, tzinfo=UTC)


def test_cu05_fecha_abre_e_cu06_exige_lista_fechada(contexto):
    produto = contexto.cadastrar_produto(1, "Quentinha", Decimal("25.50"))
    lista = contexto.criar_lista_diaria(
        1, date(2026, 10, 30), [produto.id], datetime(2026, 10, 30, 8, tzinfo=UTC)
    )

    with pytest.raises(ValidacaoDeDominioError, match="fechada"):
        contexto.gerar_relatorio_de_producao(1, lista.id)

    contexto.fechar_lista(1, lista.id)
    assert lista.status == StatusLista.FECHADA
    assert contexto.gerar_relatorio_de_producao(1, lista.id) == []

    contexto.abrir_lista(1, lista.id, datetime(2026, 10, 30, 9, tzinfo=UTC))
    assert lista.status == StatusLista.ABERTA


def test_rn05_impede_parceiro_de_operar_dados_de_outro_restaurante(contexto):
    produto = contexto.cadastrar_produto(1, "Quentinha", Decimal("25.50"))
    lista = contexto.criar_lista_diaria(
        1, date(2026, 10, 30), [produto.id], datetime(2026, 10, 30, 8, tzinfo=UTC)
    )

    with pytest.raises(AcessoNegadoError):
        contexto.atualizar_produto(2, produto.id, nome="Tentativa indevida")
    with pytest.raises(AcessoNegadoError):
        contexto.fechar_lista(2, lista.id)
    with pytest.raises(AcessoNegadoError):
        contexto.cadastrar_produto(3, "Produto", Decimal("10"))
