from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProdutoRequest(Entrada):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str = Field(default="", max_length=4000)
    preco: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    disponivel: bool = True


class ProdutoUpdate(Entrada):
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    descricao: str | None = Field(default=None, max_length=4000)
    preco: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    disponivel: bool | None = None

    @field_validator("nome", "descricao", "preco", "disponivel")
    @classmethod
    def rejeitar_null(cls, valor):
        if valor is None:
            raise ValueError("O campo não pode ser nulo; omita-o para preservar seu valor.")
        return valor


class HorariosRequest(Entrada):
    horario_abertura: time
    horario_fechamento: time

    @field_validator("horario_abertura", "horario_fechamento")
    @classmethod
    def horario_local(cls, valor):
        if valor.tzinfo is not None:
            raise ValueError("Informe o horário local sem fuso.")
        return valor


class ListaRequest(Entrada):
    data: date
    produto_ids: list[int] = Field(min_length=1, max_length=200)
    horario_abertura: time | None = None
    horario_fechamento: time | None = None

    @field_validator("horario_abertura", "horario_fechamento")
    @classmethod
    def horario_local(cls, valor):
        if valor is not None and valor.tzinfo is not None:
            raise ValueError("Informe o horário local sem fuso.")
        return valor


class ItemRequest(Entrada):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0, le=1000, strict=True)


class PedidoRequest(Entrada):
    lista_id: int = Field(gt=0)
    itens: list[ItemRequest] = Field(min_length=1, max_length=200)

    @field_validator("itens")
    @classmethod
    def itens_unicos(cls, itens):
        if len({i.produto_id for i in itens}) != len(itens):
            raise ValueError("Informe cada produto uma única vez.")
        return itens
