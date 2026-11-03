from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest

from app.domain import ListaDiaria, Produto, Restaurante, TipoCardapio, ValidacaoDeDominioError

UTC = timezone.utc


@pytest.mark.parametrize(
    ("preco", "mensagem"),
    [
        (Decimal("1.001"), "duas casas decimais"),
        (Decimal("100000000.00"), r"NUMERIC\(10, 2\)"),
    ],
)
def test_preco_respeita_numeric_10_2(preco, mensagem):
    with pytest.raises(ValidacaoDeDominioError, match=mensagem):
        Produto(1, 1, "Produto", preco)


def test_nomes_respeitam_limites_varchar_do_schema():
    with pytest.raises(ValidacaoDeDominioError, match="120"):
        Produto(1, 1, "P" * 121, Decimal("1.00"))
    with pytest.raises(ValidacaoDeDominioError, match="100"):
        Restaurante(1, "R" * 101, "Endereço", time(8), time(11), TipoCardapio.FIXO)


def test_lista_rejeita_timestamp_sem_fuso_por_usar_timestamptz():
    with pytest.raises(ValidacaoDeDominioError, match="fuso horário"):
        ListaDiaria(
            id=1,
            restaurante_id=1,
            data=date(2026, 10, 30),
            horario_abertura=datetime(2026, 10, 30, 8),
            horario_fechamento=datetime(2026, 10, 30, 11, tzinfo=UTC),
        )
