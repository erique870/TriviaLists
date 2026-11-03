"""Casos de uso da aplicação, independentes de HTTP e de banco de dados."""

from app.application.restaurante_service import ServicoRestaurante
from app.application.pedido_service import ServicoPedido

__all__ = ["ServicoPedido", "ServicoRestaurante"]
