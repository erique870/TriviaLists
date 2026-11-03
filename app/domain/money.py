"""Validação de valores compatíveis com ``NUMERIC(10, 2)`` do PostgreSQL."""

from decimal import Decimal, InvalidOperation

from app.domain.exceptions import ValidacaoDeDominioError


def numeric_10_2(valor: Decimal | int | str, campo: str) -> Decimal:
    try:
        decimal = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValidacaoDeDominioError(f"{campo} deve ser um valor monetário válido.") from None
    if not decimal.is_finite() or abs(decimal) >= Decimal("100000000"):
        raise ValidacaoDeDominioError(f"{campo} deve caber em NUMERIC(10, 2).")
    try:
        centavos = decimal.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValidacaoDeDominioError(f"{campo} deve ter no máximo duas casas decimais.") from None
    if decimal != centavos:
        raise ValidacaoDeDominioError(f"{campo} deve ter no máximo duas casas decimais.")
    return centavos
