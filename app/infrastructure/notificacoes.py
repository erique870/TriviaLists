"""Caixa de notificações e fila persistente de publicação de cardápios."""

from datetime import timedelta

from psycopg.rows import dict_row

from app.core.clock import agora
from app.domain import PapelUsuario


class NotificacoesEmMemoria:
    def __init__(self, usuarios, listas, restaurantes):
        self.usuarios, self.listas, self.restaurantes = usuarios, listas, restaurantes
        self.eventos = {}
        self.notificacoes = {}

    def agendar(self, lista_id):
        self.eventos.setdefault(lista_id, {"id": lista_id, "lista_id": lista_id, "processado": False,
                                          "enviado": False, "tentativas": 0, "proxima_tentativa": agora()})

    def distribuir(self):
        for evento in self.eventos.values():
            if evento["processado"]:
                continue
            lista = self.listas.obter_por_id(evento["lista_id"])
            restaurante = self.restaurantes.obter_por_id(lista.restaurante_id)
            for usuario in self.usuarios._usuarios.values():
                if usuario.papel == PapelUsuario.ALUNO:
                    chave = (usuario.id, lista.id)
                    self.notificacoes.setdefault(chave, {
                        "id": len(self.notificacoes) + 1, "usuario_id": usuario.id,
                        "lista_id": lista.id, "mensagem": f"{restaurante.nome} publicou o cardápio de {lista.data:%d/%m/%Y}.",
                        "criada_em": agora(), "lida": False,
                    })
            evento["processado"] = True

    def listar(self, usuario_id):
        return sorted([n.copy() for n in self.notificacoes.values() if n["usuario_id"] == usuario_id],
                      key=lambda n: n["id"], reverse=True)[:100]

    def marcar_lida(self, usuario_id, notificacao_id):
        for n in self.notificacoes.values():
            if n["id"] == notificacao_id and n["usuario_id"] == usuario_id:
                n["lida"] = True
                return True
        return False

    def pendentes_externos(self):
        return [e.copy() for e in self.eventos.values()
                if e["processado"] and not e["enviado"] and e["proxima_tentativa"] <= agora()][:20]

    def registrar_envio(self, evento_id, sucesso):
        e = self.eventos[evento_id]
        e["enviado"] = sucesso
        e["tentativas"] += 1
        e["proxima_tentativa"] = agora() + timedelta(seconds=min(3600, 30 * 2 ** min(e["tentativas"], 7)))


class NotificacoesPostgres:
    def __init__(self, db):
        self.db = db

    def agendar(self, lista_id):
        with self.db.conexao() as conn:
            conn.execute("INSERT INTO eventos_cardapio (lista_id) VALUES (%s) ON CONFLICT (lista_id) DO NOTHING", (lista_id,))

    def distribuir(self):
        with self.db.transacao(), self.db.conexao() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""SELECT e.id, e.lista_id, r.nome, l.data FROM eventos_cardapio e
                           JOIN listas_diarias l ON l.id=e.lista_id JOIN restaurantes r ON r.id=l.restaurante_id
                           WHERE NOT e.processado ORDER BY e.id LIMIT 20 FOR UPDATE OF e SKIP LOCKED""")
            for evento in cur.fetchall():
                conn.execute("""INSERT INTO notificacoes (usuario_id, lista_id, mensagem)
                                SELECT id, %s, %s FROM usuarios WHERE papel='ALUNO'
                                ON CONFLICT (usuario_id, lista_id) DO NOTHING""",
                             (evento["lista_id"], f"{evento['nome']} publicou o cardápio de {evento['data']:%d/%m/%Y}."))
                conn.execute("UPDATE eventos_cardapio SET processado=TRUE WHERE id=%s", (evento["id"],))

    def listar(self, usuario_id):
        with self.db.conexao() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM notificacoes WHERE usuario_id=%s ORDER BY id DESC LIMIT 100", (usuario_id,))
            return cur.fetchall()

    def marcar_lida(self, usuario_id, notificacao_id):
        with self.db.conexao() as conn:
            return conn.execute("UPDATE notificacoes SET lida=TRUE WHERE id=%s AND usuario_id=%s",
                                (notificacao_id, usuario_id)).rowcount > 0

    def pendentes_externos(self):
        with self.db.conexao() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""SELECT id, lista_id FROM eventos_cardapio WHERE processado AND NOT enviado
                           AND proxima_tentativa <= NOW() ORDER BY id LIMIT 20""")
            return cur.fetchall()

    def registrar_envio(self, evento_id, sucesso):
        with self.db.conexao() as conn:
            conn.execute("""UPDATE eventos_cardapio SET enviado=%s, tentativas=tentativas+1,
                            proxima_tentativa=NOW() + LEAST(3600, 30 * POWER(2, LEAST(tentativas+1, 7))) * INTERVAL '1 second'
                            WHERE id=%s""", (sucesso, evento_id))
