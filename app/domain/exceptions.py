from __future__ import annotations


class ErroDominio(ValueError):
    """Erro de domínio com identificador estável e referência às regras."""

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str,
        regras: tuple[str, ...] = (),
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo
        self.regras = regras

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "codigo": self.codigo,
            "mensagem": self.mensagem,
            "regras": list(self.regras),
        }


class RegraDeNegocioError(ErroDominio):
    """Base para violações de regras de negócio."""

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str = "regra_de_negocio_invalida",
        regras: tuple[str, ...] = (),
    ) -> None:
        super().__init__(mensagem, codigo=codigo, regras=regras)


class ValidacaoDeDominioError(ErroDominio):
    """Erro de validação que não corresponde a uma RN específica."""

    def __init__(self, mensagem: str, *, codigo: str = "dados_invalidos") -> None:
        super().__init__(mensagem, codigo=codigo)


class HorarioLimiteExcedidoError(RegraDeNegocioError):
    def __init__(self, mensagem: str | None = None) -> None:
        super().__init__(
            mensagem
            or "O horário limite para pedidos e cancelamentos desta lista foi ultrapassado.",
            codigo="horario_limite_excedido",
            regras=("RN01", "RN04"),
        )


class PedidoAtivoExistenteError(RegraDeNegocioError):
    def __init__(self, mensagem: str | None = None) -> None:
        super().__init__(
            mensagem or "Você já possui um pedido ativo para esta lista.",
            codigo="pedido_ativo_existente",
            regras=("RN03",),
        )


class AcessoNegadoError(RegraDeNegocioError):
    def __init__(self, mensagem: str | None = None) -> None:
        super().__init__(
            mensagem or "Você não tem permissão para realizar esta operação.",
            codigo="acesso_negado",
            regras=("RN05",),
        )
