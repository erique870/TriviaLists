from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.enums import StatusPedido, StatusRetirada
from app.domain.exceptions import RegraDeNegocioError, ValidacaoDeDominioError
from app.domain.item_pedido import ItemPedido
from app.domain.money import numeric_10_2


@dataclass(slots=True)
class Pedido:
    id: int
    lista_diaria_id: int
    usuario_id: int
    data_hora_pedido: datetime
    itens: list[ItemPedido]
    status: StatusPedido = StatusPedido.ATIVO
    status_retirada: StatusRetirada = StatusRetirada.PENDENTE
    valor_total: Decimal = field(init=False)

    def __post_init__(self) -> None:
        if not self.itens:
            raise ValidacaoDeDominioError("Pedido precisa conter ao menos um item.")
        self.valor_total = self.calcular_total()
        self.valor_total = numeric_10_2(self.valor_total, "Total do pedido")
        for item in self.itens:
            item.pedido_id = self.id

    def calcular_total(self) -> Decimal:
        return sum((item.calcular_subtotal() for item in self.itens), Decimal("0.00"))

    def confirmar_retirada(self) -> None:
        if self.status != StatusPedido.ATIVO:
            raise RegraDeNegocioError(
                "Pedido cancelado não pode ser retirado.",
                codigo="pedido_cancelado",
            )
        self.status_retirada = StatusRetirada.RETIRADO
