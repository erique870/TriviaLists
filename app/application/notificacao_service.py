"""Distribuição assíncrona com repetição de envios externos que falharem."""

import json
import logging
from urllib.request import Request, urlopen

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServicoNotificacao:
    def __init__(self, contexto):
        self.contexto = contexto

    def processar(self):
        with self.contexto.transacao():
            self.contexto.notificacoes.distribuir()
        if not settings.NOTIFICATION_WEBHOOK_URL:
            return
        for evento in self.contexto.notificacoes.pendentes_externos():
            lista = self.contexto.listas.obter_por_id(evento["lista_id"])
            restaurante = self.contexto.restaurantes.obter_por_id(lista.restaurante_id)
            payload = {"evento_id": evento["id"], "tipo": "cardapio_publicado", "lista_id": lista.id,
                       "restaurante_id": restaurante.id, "restaurante": restaurante.nome,
                       "data": lista.data.isoformat(), "url": "/aluno"}
            headers = {"Content-Type": "application/json", "Idempotency-Key": f"cardapio-{evento['id']}"}
            if settings.NOTIFICATION_WEBHOOK_TOKEN:
                headers["Authorization"] = f"Bearer {settings.NOTIFICATION_WEBHOOK_TOKEN}"
            sucesso = False
            try:
                req = Request(settings.NOTIFICATION_WEBHOOK_URL, data=json.dumps(payload).encode(), headers=headers, method="POST")
                with urlopen(req, timeout=5) as resposta:
                    sucesso = 200 <= resposta.status < 300
            except Exception:
                logger.warning("Não foi possível entregar o evento de cardápio %s; o envio será repetido.", evento["id"])
            self.contexto.notificacoes.registrar_envio(evento["id"], sucesso)
