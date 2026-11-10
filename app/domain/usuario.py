from dataclasses import dataclass

from app.domain.enums import PapelUsuario
from app.domain.exceptions import ValidacaoDeDominioError


@dataclass(slots=True)
class Usuario:
    id: int
    nome: str
    email: str
    senha_hash: str
    telefone: str
    papel: PapelUsuario
    restaurante_id: int | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip() or not self.email.strip() or not self.senha_hash:
            raise ValidacaoDeDominioError(
                "Nome, e-mail e hash da senha são obrigatórios."
            )
        if self.papel == PapelUsuario.CLIENTE and self.restaurante_id is not None:
            raise ValidacaoDeDominioError(
                "Cliente não pode estar associado a um restaurante."
            )
        if self.papel == PapelUsuario.PARCEIRO and self.restaurante_id is None:
            raise ValidacaoDeDominioError(
                "Parceiro deve estar associado a um restaurante."
            )
