"""Traduz as falhas de validação do Pydantic para mensagens exibíveis ao usuário.

O FastAPI devolve `detail` como lista de objetos técnicos, em inglês. Aqui a
lista vira uma frase única em português, no mesmo formato de texto usado pelos
demais handlers de ``app.main``.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

ROTULOS: dict[str, str] = {
    "nome": "Nome",
    "email": "E-mail",
    "telefone": "Telefone",
    "senha": "Senha",
    "preco": "Preço",
    "descricao": "Descrição",
    "disponivel": "Disponibilidade",
    "data": "Data",
    "produto_ids": "Produtos",
    "produto_id": "Produto",
    "quantidade": "Quantidade",
    "lista_id": "Lista",
    "itens": "Itens",
    "horario_abertura": "Horário de abertura",
    "horario_fechamento": "Horário de fechamento",
}

_FRAGMENTOS: dict[str, str] = {
    "missing": "é obrigatório",
    "extra_forbidden": "não é aceito neste formulário",
    "decimal_parsing": "precisa ser um número",
    "time_parsing": "precisa ser um horário válido",
    "bool_parsing": "precisa ser verdadeiro ou falso",
    "bool_type": "precisa ser verdadeiro ou falso",
    "string_type": "precisa ser um texto",
}


def _rotulo(loc: Sequence[Any]) -> str:
    """Nome amigável do campo. Ignora o prefixo de origem e os índices de lista."""
    campo = next(
        (str(parte) for parte in reversed(tuple(loc)[1:]) if not isinstance(parte, int)),
        "",
    )
    return ROTULOS.get(campo) or campo.replace("_", " ").capitalize() or "Dados"


def _fragmento(tipo: str, ctx: dict[str, Any]) -> str:
    if tipo == "string_too_short":
        return f"precisa de ao menos {ctx.get('min_length')} caracteres"
    if tipo == "string_too_long":
        return f"aceita no máximo {ctx.get('max_length')} caracteres"
    if tipo == "too_short":
        return f"precisa de ao menos {ctx.get('min_length')} item"
    if tipo == "too_long":
        return f"aceita no máximo {ctx.get('max_length')} itens"
    if tipo == "greater_than":
        return f"precisa ser maior que {ctx.get('gt')}"
    if tipo == "greater_than_equal":
        return f"não pode ser menor que {ctx.get('ge')}"
    if tipo == "less_than":
        return f"precisa ser menor que {ctx.get('lt')}"
    if tipo == "less_than_equal":
        return f"não pode ser maior que {ctx.get('le')}"
    if tipo.startswith("date_"):
        return "precisa ser uma data válida"
    if tipo.startswith("int_"):
        return "precisa ser um número inteiro"
    return _FRAGMENTOS.get(tipo, "não é válido")


def mensagem_de_validacao(erros: Iterable[dict[str, Any]]) -> str:
    """Junta os erros de um ``RequestValidationError`` numa frase em português."""
    partes: list[str] = []
    for item in erros:
        tipo = item.get("type", "")
        if tipo == "value_error":
            # Já é uma frase completa, escrita no `field_validator` do schema.
            partes.append(str(item.get("msg", "")).removeprefix("Value error, "))
            continue
        ctx = item.get("ctx") or {}
        partes.append(f"{_rotulo(item.get('loc', ()))} {_fragmento(tipo, ctx)}")
    return "; ".join(partes) or "Dados inválidos."
