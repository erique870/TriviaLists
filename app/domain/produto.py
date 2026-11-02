from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions import ValidacaoDeDominioError


@dataclass(slots=True)
class Produto:
    id: int
    restaurante_id: int
    nome: str
    preco: Decimal
    descricao: str = ""
    disponivel: bool = True

    def __post_init__(self) -> None:
        self.preco = Decimal(str(self.preco))
        if self.preco < 0:
            raise ValidacaoDeDominioError("O preço do produto não pode ser negativo.")
        if not self.nome.strip():
            raise ValidacaoDeDominioError("Produto precisa ter um nome.")

    def obter_preco(self) -> Decimal:
        return self.preco
