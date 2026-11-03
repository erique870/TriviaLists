from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions import ValidacaoDeDominioError
from app.domain.money import numeric_10_2


@dataclass(slots=True)
class Produto:
    id: int
    restaurante_id: int
    nome: str
    preco: Decimal
    descricao: str = ""
    disponivel: bool = True

    def __post_init__(self) -> None:
        self.preco = numeric_10_2(self.preco, "Preço do produto")
        if self.preco < 0:
            raise ValidacaoDeDominioError("O preço do produto não pode ser negativo.")
        if not self.nome.strip():
            raise ValidacaoDeDominioError("Produto precisa ter um nome.")
        if len(self.nome) > 120:
            raise ValidacaoDeDominioError("Nome do produto deve ter até 120 caracteres.")

    def obter_preco(self) -> Decimal:
        return self.preco
