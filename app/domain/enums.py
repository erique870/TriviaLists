from enum import StrEnum


class PapelUsuario(StrEnum):
    CLIENTE = "CLIENTE"
    PARCEIRO = "PARCEIRO"


class TipoCardapio(StrEnum):
    FIXO = "FIXO"
    VARIAVEL = "VARIAVEL"


class StatusLista(StrEnum):
    ABERTA = "ABERTA"
    FECHADA = "FECHADA"


class StatusPedido(StrEnum):
    ATIVO = "ATIVO"
    CANCELADO = "CANCELADO"


class StatusRetirada(StrEnum):
    PENDENTE = "PENDENTE"
    RETIRADO = "RETIRADO"
