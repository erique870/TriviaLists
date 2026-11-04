"""Repositórios PostgreSQL para o schema de ``database/schema.sql``."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.domain import (
    ItemPedido,
    ListaDiaria,
    PapelUsuario,
    PedidoAtivoExistenteError,
    Pedido,
    Produto,
    Restaurante,
    StatusLista,
    StatusPedido,
    StatusRetirada,
    TipoCardapio,
    Usuario,
)


class RepositoriosPostgres:
    """Implementa as portas de persistência do domínio."""

    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return Usuario(
            id=row["id"], nome=row["nome"], email=row["email"],
            senha_hash=row["senha_hash"], telefone=row["telefone"],
            papel=PapelUsuario(row["papel"]), restaurante_id=row["restaurante_id"],
        )

    def obter_usuario_por_email(self, email: str) -> Usuario | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM usuarios WHERE LOWER(email) = LOWER(%s)", (email.strip(),))
            row = cur.fetchone()
        if row is None:
            return None
        return Usuario(
            id=row["id"], nome=row["nome"], email=row["email"],
            senha_hash=row["senha_hash"], telefone=row["telefone"],
            papel=PapelUsuario(row["papel"]), restaurante_id=row["restaurante_id"],
        )

    def salvar_usuario(self, usuario: Usuario) -> Usuario:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            if usuario.id is None or usuario.id == 0:
                cur.execute(
                    """INSERT INTO usuarios (nome, email, senha_hash, telefone, papel, restaurante_id)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (usuario.nome, usuario.email.strip().lower(), usuario.senha_hash,
                     usuario.telefone, usuario.papel.value, usuario.restaurante_id),
                )
                novo_id = cur.fetchone()["id"]
                conn.commit()
                return Usuario(
                    id=novo_id, nome=usuario.nome, email=usuario.email.strip().lower(),
                    senha_hash=usuario.senha_hash, telefone=usuario.telefone,
                    papel=usuario.papel, restaurante_id=usuario.restaurante_id,
                )
            else:
                cur.execute(
                    """UPDATE usuarios SET nome=%s, email=%s, senha_hash=%s,
                       telefone=%s, papel=%s, restaurante_id=%s WHERE id=%s""",
                    (usuario.nome, usuario.email.strip().lower(), usuario.senha_hash,
                     usuario.telefone, usuario.papel.value, usuario.restaurante_id, usuario.id),
                )
                conn.commit()
                return usuario

    def obter_restaurante(self, restaurante_id: int) -> Restaurante | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM restaurantes WHERE id = %s", (restaurante_id,))
            row = cur.fetchone()
        if row is None:
            return None
        return Restaurante(
            id=row["id"], nome=row["nome"], endereco=row["endereco"],
            horario_padrao_abertura=row["horario_padrao_abertura"],
            horario_padrao_fechamento=row["horario_padrao_fechamento"],
            tipo_cardapio=TipoCardapio(row["tipo_cardapio"]), ativo=row["ativo"],
        )

    def salvar_restaurante(self, restaurante: Restaurante) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """UPDATE restaurantes SET nome=%s, endereco=%s,
                   horario_padrao_abertura=%s, horario_padrao_fechamento=%s,
                   tipo_cardapio=%s, ativo=%s WHERE id=%s""",
                (restaurante.nome, restaurante.endereco,
                 restaurante.horario_padrao_abertura, restaurante.horario_padrao_fechamento,
                 restaurante.tipo_cardapio.value, restaurante.ativo, restaurante.id),
            )

    def proximo_id_produto(self) -> int:
        return self._proximo_id("produtos_id_seq")

    def obter_produto(self, produto_id: int) -> Produto | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
            row = cur.fetchone()
        return self._produto(row) if row else None

    def listar_por_restaurante(self, restaurante_id: int) -> list[Produto]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM produtos WHERE restaurante_id = %s ORDER BY id", (restaurante_id,))
            return [self._produto(row) for row in cur.fetchall()]

    def salvar_produto(self, produto: Produto) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """INSERT INTO produtos (id, restaurante_id, nome, descricao, preco, disponivel)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET nome=EXCLUDED.nome,
                   descricao=EXCLUDED.descricao, preco=EXCLUDED.preco,
                   disponivel=EXCLUDED.disponivel""",
                (produto.id, produto.restaurante_id, produto.nome, produto.descricao,
                 produto.preco, produto.disponivel),
            )

    def proximo_id_lista(self) -> int:
        return self._proximo_id("listas_diarias_id_seq")

    def proximo_id_pedido(self) -> int:
        return self._proximo_id("pedidos_id_seq")

    def obter_pedido(self, pedido_id: int) -> Pedido | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM pedidos WHERE id=%s", (pedido_id,))
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT * FROM itens_pedido WHERE pedido_id=%s ORDER BY id", (pedido_id,)
            )
            itens = [
                ItemPedido(
                    produto_id=item["produto_id"],
                    quantidade=item["quantidade"],
                    preco_unitario=Decimal(item["preco_unitario"]),
                    id=item["id"], pedido_id=pedido_id,
                )
                for item in cur.fetchall()
            ]
        if not itens:
            return None
        return Pedido(
            id=row["id"], lista_diaria_id=row["lista_diaria_id"],
            usuario_id=row["usuario_id"], data_hora_pedido=row["data_hora_pedido"],
            itens=itens, status=StatusPedido(row["status"]),
            status_retirada=StatusRetirada(row["status_retirada"]),
        )

    def listar_pedidos_por_usuario(self, usuario_id: int) -> list[Pedido]:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id FROM pedidos WHERE usuario_id=%s ORDER BY data_hora_pedido DESC, id DESC",
                (usuario_id,),
            )
            pedido_ids = [row["id"] for row in cur.fetchall()]
        return [pedido for pedido_id in pedido_ids
                if (pedido := self.obter_pedido(pedido_id)) is not None]

    def salvar_pedido(self, pedido: Pedido) -> None:
        try:
            with self.pool.connection() as conn:
                conn.execute(
                    """INSERT INTO pedidos
                       (id, lista_diaria_id, usuario_id, data_hora_pedido, valor_total,
                        status, status_retirada)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET valor_total=EXCLUDED.valor_total,
                       status=EXCLUDED.status, status_retirada=EXCLUDED.status_retirada""",
                    (pedido.id, pedido.lista_diaria_id, pedido.usuario_id,
                     pedido.data_hora_pedido, pedido.valor_total, pedido.status.value,
                     pedido.status_retirada.value),
                )
                conn.execute("DELETE FROM itens_pedido WHERE pedido_id=%s", (pedido.id,))
                conn.executemany(
                    """INSERT INTO itens_pedido
                       (pedido_id, produto_id, quantidade, preco_unitario)
                       VALUES (%s, %s, %s, %s)""",
                    [(pedido.id, item.produto_id, item.quantidade, item.preco_unitario)
                     for item in pedido.itens],
                )
        except UniqueViolation as erro:
            if erro.diag.constraint_name == "uk_pedido_ativo":
                raise PedidoAtivoExistenteError() from erro
            raise

    def obter_lista(self, lista_id: int) -> ListaDiaria | None:
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM listas_diarias WHERE id = %s", (lista_id,))
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                """SELECT p.* FROM produtos p JOIN lista_produtos lp ON lp.produto_id=p.id
                   WHERE lp.lista_diaria_id=%s ORDER BY p.id""", (lista_id,),
            )
            produtos = {p["id"]: self._produto(p) for p in cur.fetchall()}
            cur.execute(
                """SELECT pe.*, ip.id AS item_id, ip.produto_id, ip.quantidade,
                          ip.preco_unitario
                   FROM pedidos pe LEFT JOIN itens_pedido ip ON ip.pedido_id=pe.id
                   WHERE pe.lista_diaria_id=%s ORDER BY pe.id, ip.id""", (lista_id,),
            )
            pedidos_dados: dict[int, dict] = {}
            for pedido_row in cur.fetchall():
                dados = pedidos_dados.setdefault(
                    pedido_row["id"],
                    {
                        "usuario_id": pedido_row["usuario_id"],
                        "data_hora_pedido": pedido_row["data_hora_pedido"],
                        "status": StatusPedido(pedido_row["status"]),
                        "status_retirada": StatusRetirada(pedido_row["status_retirada"]),
                        "itens": [],
                    },
                )
                if pedido_row["item_id"] is not None:
                    dados["itens"].append(ItemPedido(
                        produto_id=pedido_row["produto_id"],
                        quantidade=pedido_row["quantidade"],
                        preco_unitario=Decimal(pedido_row["preco_unitario"]),
                        id=pedido_row["item_id"], pedido_id=pedido_row["id"],
                    ))
            pedidos = [
                Pedido(
                    id=pedido_id, lista_diaria_id=lista_id,
                    usuario_id=dados["usuario_id"],
                    data_hora_pedido=dados["data_hora_pedido"],
                    itens=dados["itens"], status=dados["status"],
                    status_retirada=dados["status_retirada"],
                )
                for pedido_id, dados in pedidos_dados.items()
                if dados["itens"]
            ]
            lista = ListaDiaria(
                id=row["id"], restaurante_id=row["restaurante_id"], data=row["data"],
                horario_abertura=row["horario_abertura"],
                horario_fechamento=row["horario_fechamento"],
                status=StatusLista(row["status"]), produtos=produtos,
                pedidos=pedidos,
            )
        return lista

    def listar_listas_abertas(
        self, data_hora: datetime, restaurante_id: int | None = None
    ) -> list[ListaDiaria]:
        sql = """SELECT id FROM listas_diarias
                 WHERE status='ABERTA' AND horario_abertura <= %s
                   AND horario_fechamento > %s"""
        params: tuple = (data_hora, data_hora)
        if restaurante_id is not None:
            sql += " AND restaurante_id=%s"
            params += (restaurante_id,)
        sql += " ORDER BY horario_fechamento, id"
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            lista_ids = [row["id"] for row in cur.fetchall()]
        return [lista for lista_id in lista_ids
                if (lista := self.obter_lista(lista_id)) is not None]

    def salvar_lista(self, lista: ListaDiaria) -> None:
        """Salva lista e vínculos em uma transação."""
        with self.pool.connection() as conn:
            conn.execute(
                """INSERT INTO listas_diarias
                   (id, restaurante_id, data, horario_abertura, horario_fechamento, status)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data,
                   horario_abertura=EXCLUDED.horario_abertura,
                   horario_fechamento=EXCLUDED.horario_fechamento,
                   status=EXCLUDED.status""",
                (lista.id, lista.restaurante_id, lista.data, lista.horario_abertura,
                 lista.horario_fechamento, lista.status.value),
            )
            conn.execute("DELETE FROM lista_produtos WHERE lista_diaria_id=%s", (lista.id,))
            conn.executemany(
                "INSERT INTO lista_produtos (lista_diaria_id, produto_id) VALUES (%s, %s)",
                [(lista.id, produto_id) for produto_id in lista.produtos],
            )

    def _proximo_id(self, sequence: str) -> int:
        # O nome de sequence é selecionado internamente, nunca vem de entrada HTTP.
        with self.pool.connection() as conn:
            row = conn.execute("SELECT nextval(%s::regclass)", (sequence,)).fetchone()
        return int(row[0])

    @staticmethod
    def _produto(row: dict) -> Produto:
        return Produto(
            id=row["id"], restaurante_id=row["restaurante_id"], nome=row["nome"],
            descricao=row["descricao"] or "", preco=Decimal(row["preco"]),
            disponivel=row["disponivel"],
        )


class RepositorioUsuarioPostgres:
    def __init__(self, db: RepositoriosPostgres) -> None:
        self.db = db

    def obter_por_id(self, usuario_id: int) -> Usuario | None:
        return self.db.obter_por_id(usuario_id)

    def obter_por_email(self, email: str) -> Usuario | None:
        return self.db.obter_usuario_por_email(email)

    def salvar(self, usuario: Usuario) -> Usuario:
        return self.db.salvar_usuario(usuario)


class RepositorioRestaurantePostgres:
    def __init__(self, db: RepositoriosPostgres) -> None:
        self.db = db

    def obter_por_id(self, restaurante_id: int) -> Restaurante | None:
        return self.db.obter_restaurante(restaurante_id)

    def salvar(self, restaurante: Restaurante) -> None:
        self.db.salvar_restaurante(restaurante)


class RepositorioProdutoPostgres:
    def __init__(self, db: RepositoriosPostgres) -> None:
        self.db = db

    def proximo_id(self) -> int:
        return self.db.proximo_id_produto()

    def obter_por_id(self, produto_id: int) -> Produto | None:
        return self.db.obter_produto(produto_id)

    def listar_por_restaurante(self, restaurante_id: int) -> list[Produto]:
        return self.db.listar_por_restaurante(restaurante_id)

    def salvar(self, produto: Produto) -> None:
        self.db.salvar_produto(produto)


class RepositorioListaDiariaPostgres:
    def __init__(self, db: RepositoriosPostgres) -> None:
        self.db = db

    def proximo_id(self) -> int:
        return self.db.proximo_id_lista()

    def obter_por_id(self, lista_id: int) -> ListaDiaria | None:
        return self.db.obter_lista(lista_id)

    def listar_abertas(
        self, data_hora: datetime, restaurante_id: int | None = None
    ) -> list[ListaDiaria]:
        return self.db.listar_listas_abertas(data_hora, restaurante_id)

    def salvar(self, lista: ListaDiaria) -> None:
        self.db.salvar_lista(lista)


class RepositorioPedidoPostgres:
    def __init__(self, db: RepositoriosPostgres) -> None:
        self.db = db

    def proximo_id(self) -> int:
        return self.db.proximo_id_pedido()

    def obter_por_id(self, pedido_id: int) -> Pedido | None:
        return self.db.obter_pedido(pedido_id)

    def listar_por_usuario(self, usuario_id: int) -> list[Pedido]:
        return self.db.listar_pedidos_por_usuario(usuario_id)

    def salvar(self, pedido: Pedido) -> None:
        self.db.salvar_pedido(pedido)
