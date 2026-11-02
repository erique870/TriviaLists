from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions import ValidacaoDeDominioError


@dataclass(slots=True)
class ItemPedido:
    produto_id: int
    quantidade: int
    preco_unitario: Decimal
    id: int | None = None
    pedido_id: int | None = None

    def __post_init__(self) -> None:
        self.preco_unitario = Decimal(str(self.preco_unitario))
        if self.quantidade <= 0:
            raise ValidacaoDeDominioError(
                "A quantidade do item deve ser maior que zero."
            )
        if self.preco_unitario < 0:
            raise ValidacaoDeDominioError("O preço unitário não pode ser negativo.")

    def calcular_subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade
