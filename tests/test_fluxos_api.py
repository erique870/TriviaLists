"""Aceitação dos casos de uso, passando por HTTP, sessão, serviço e repositórios."""

from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from app.application.cliente_service import ServicoCliente
from app.application.notificacao_service import ServicoNotificacao
from app.application.restaurante_service import ServicoRestaurante
from app.core.security import gerar_hash_senha
from app.domain import PapelUsuario, Restaurante, TipoCardapio, Usuario
from app.infrastructure.contexto import contexto_memoria
from app.main import create_app
from app.routers import operacoes

FIXO = datetime(2026, 11, 4, 9, tzinfo=ZoneInfo("America/Sao_Paulo"))


def preparar(ctx):
    senha = gerar_hash_senha("senha123")
    for rid in (1, 2):
        ctx.restaurantes.salvar(Restaurante(rid, f"Restaurante {rid}", "Campus", time(8), time(11),
                                           TipoCardapio.VARIAVEL if rid == 1 else TipoCardapio.FIXO))
    for uid, papel, rid in [(1, PapelUsuario.PARCEIRO, 1), (2, PapelUsuario.PARCEIRO, 2),
                             (3, PapelUsuario.CLIENTE, None), (4, PapelUsuario.CLIENTE, None)]:
        ctx.usuarios.salvar(Usuario(uid, f"Usuário {uid}", f"u{uid}@exemplo.com", senha, "21999999999", papel, rid))


@contextmanager
def persistencia(tipo):
    if tipo == "memoria":
        yield contexto_memoria()
        return
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para executar a integração PostgreSQL.")
    from psycopg import connect, sql
    from psycopg_pool import ConnectionPool
    from app.infrastructure.contexto import contexto_postgres
    from app.infrastructure.postgres import RepositoriosPostgres
    schema = "teste_" + uuid4().hex
    with connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with ConnectionPool(url, min_size=1, max_size=5, kwargs={"options": f"-csearch_path={schema}"}) as pool:
                with pool.connection() as db:
                    db.execute(Path("database/schema.sql").read_text())
                yield contexto_postgres(RepositoriosPostgres(pool))
        finally:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


@pytest.fixture(params=["memoria", "postgres"])
def ambiente(monkeypatch, request):
    from app.core.config import settings
    monkeypatch.setattr(settings, "NOTIFICATION_WEBHOOK_URL", "")
    relogio = [FIXO]
    with persistencia(request.param) as ctx:
        preparar(ctx)
        app = create_app(ctx, executar_tarefas=False)
        app.dependency_overrides[operacoes.cliente] = lambda: ServicoCliente(ctx, lambda: relogio[0])
        monkeypatch.setattr(operacoes, "agora", lambda: relogio[0])
        with TestClient(app) as client:
            headers = {}
            for uid in range(1, 5):
                r = client.post("/auth/login", json={"email": f"u{uid}@exemplo.com", "senha": "senha123"})
                assert r.status_code == 200
                headers[uid] = {"Authorization": "Bearer " + r.json()["access_token"]}
            yield client, ctx, headers, relogio


def publicar(client, headers, **alteracoes):
    produto = client.post("/api/parceiro/produtos", headers=headers[1],
                          json={"nome": "Quentinha", "preco": "25.50", "descricao": "Frango"})
    assert produto.status_code == 201, produto.text
    dados = {"data": "2026-11-04", "produto_ids": [produto.json()["id"]], **alteracoes}
    lista = client.post("/api/parceiro/listas", headers=headers[1], json=dados)
    assert lista.status_code == 201, lista.text
    return produto.json(), lista.json()


def test_fluxo_completo_publicar_pedir_cancelar_refazer_fechar_e_relatorio(ambiente):
    client, ctx, h, _ = ambiente
    vazio = client.get("/api/listas", headers=h[3]).json()
    assert vazio["listas"] == []
    assert "Nenhum restaurante" in vazio["mensagem"]
    produto, lista = publicar(client, h)
    assert client.get("/api/listas", headers=h[3]).json()["listas"][0]["id"] == lista["id"]
    assert client.get("/api/listas?restaurante_id=2", headers=h[3]).json()["listas"] == []
    # RF06: publicação chega aos clientes, com marcação de leitura isolada por usuário.
    avisos = client.get("/api/notificacoes", headers=h[3]).json()
    assert len(avisos) == 1 and not avisos[0]["lida"]
    assert client.post(f"/api/notificacoes/{avisos[0]['id']}/ler", headers=h[4]).status_code == 404
    assert client.post(f"/api/notificacoes/{avisos[0]['id']}/ler", headers=h[3]).status_code == 200
    dados = {"lista_id": lista["id"], "itens": [{"produto_id": produto["id"], "quantidade": 2}]}
    r = client.post("/api/pedidos", headers=h[3], json=dados)
    assert r.status_code == 201, r.text
    pedido = r.json()
    assert Decimal(str(pedido["valor_total"])) == Decimal("51.00")
    assert pedido["status_retirada"] == "PENDENTE"
    assert client.post("/api/pedidos", headers=h[3], json=dados).status_code == 409
    assert client.get(f"/api/pedidos/{pedido['id']}", headers=h[4]).status_code == 404
    assert client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[4]).status_code == 403
    assert client.get("/api/pedidos", headers=h[4]).json() == []
    assert client.patch(f"/api/parceiro/produtos/{produto['id']}", headers=h[1], json={"preco": "30.00"}).status_code == 200
    antigo = client.get(f"/api/pedidos/{pedido['id']}", headers=h[3]).json()
    assert Decimal(str(antigo["itens"][0]["preco_unitario"])) == Decimal("25.50")
    assert client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[3]).json()["status"] == "CANCELADO"
    novo = client.post("/api/pedidos", headers=h[3], json=dados)
    assert novo.status_code == 201 and novo.json()["id"] != pedido["id"]
    assert Decimal(str(novo.json()["valor_total"])) == Decimal("60.00")
    assert client.get(f"/api/parceiro/listas/{lista['id']}/relatorio", headers=h[1]).status_code == 409
    fechado = client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1])
    assert fechado.status_code == 200, fechado.text
    relatorio = fechado.json()["relatorio"]
    assert relatorio["itens"][0]["quantidade"] == 2
    assert Decimal(str(relatorio["valor_total"])) == Decimal("60.00")
    assert relatorio["total_pedidos"] == 1
    assert client.post("/api/pedidos", headers=h[4], json=dados).status_code == 409
    assert client.post(f"/api/pedidos/{novo.json()['id']}/cancelar", headers=h[3]).status_code == 409
    assert client.post(f"/api/parceiro/listas/{lista['id']}/abrir", headers=h[1]).status_code == 200


def test_isolamento_de_papeis_restaurantes_e_dados_injetados(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    assert client.get("/api/listas").status_code == 401
    assert client.get("/api/listas", headers=h[1]).status_code == 403
    assert client.get("/api/parceiro/produtos", headers=h[3]).status_code == 403
    assert client.patch(f"/api/parceiro/produtos/{produto['id']}", headers=h[2], json={"nome": "Invasão"}).status_code == 403
    for acao in ("abrir", "fechar"):
        assert client.post(f"/api/parceiro/listas/{lista['id']}/{acao}", headers=h[2]).status_code == 403
    assert client.get(f"/api/parceiro/listas/{lista['id']}/relatorio", headers=h[2]).status_code == 403
    assert client.post("/api/parceiro/listas", headers=h[2], json={"data": "2026-11-04", "produto_ids": [produto["id"]]}).status_code == 403
    assert client.post("/api/parceiro/produtos", headers=h[1], json={"nome": "X", "preco": 1, "restaurante_id": 2}).status_code == 422
    assert client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"], "usuario_id": 4, "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).status_code == 422
    assert client.get("/api/parceiro/listas", headers=h[2]).json() == []


@pytest.mark.parametrize("alteracao", [{"preco": "-1"}, {"nome": "   "}, {"preco": "NaN"}, {"preco": "1.001"}])
def test_produto_rejeita_dados_invalidos(ambiente, alteracao):
    client, _, h, _ = ambiente
    assert client.post("/api/parceiro/produtos", headers=h[1], json={"nome": "Quentinha", "preco": "25", **alteracao}).status_code == 422


def test_prazo_publicacao_tardia_e_fechamento_automatico(ambiente):
    client, ctx, h, relogio = ambiente
    produto, lista = publicar(client, h)
    dados = {"lista_id": lista["id"], "itens": [{"produto_id": produto["id"], "quantidade": 1}]}
    pedido = client.post("/api/pedidos", headers=h[3], json=dados).json()
    relogio[0] = FIXO.replace(hour=11)
    assert client.get("/api/listas", headers=h[3]).json()["listas"] == []
    assert client.post("/api/pedidos", headers=h[4], json=dados).status_code == 403
    assert client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[3]).status_code == 403
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao)
    assert servico.encerrar_expiradas(relogio[0])[0]["total_pedidos"] == 1
    assert servico.encerrar_expiradas(relogio[0]) == []
    assert client.post(f"/api/parceiro/listas/{lista['id']}/abrir", headers=h[1]).status_code == 422
    relogio[0] = FIXO.replace(hour=11, minute=10)
    _, tardia = publicar(client, h)
    assert datetime.fromisoformat(tardia["horario_fechamento"]).hour == 11
    assert datetime.fromisoformat(tardia["horario_fechamento"]).minute == 40
    p = client.post("/api/parceiro/produtos", headers=h[2], json={"nome": "Fixo", "preco": 10}).json()
    assert client.post("/api/parceiro/listas", headers=h[2], json={"data": "2026-11-04", "produto_ids": [p["id"]]}).status_code == 422


def test_itens_invalidos_nao_deixam_pedido_parcial_e_produto_desativado(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    itens = [{"produto_id": produto["id"], "quantidade": 1}, {"produto_id": 99999, "quantidade": 1}]
    assert client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"], "itens": itens}).status_code == 422
    assert client.get("/api/pedidos", headers=h[3]).json() == []
    assert client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"], "itens": itens[:1] * 2}).status_code == 422
    client.patch(f"/api/parceiro/produtos/{produto['id']}", headers=h[1], json={"disponivel": False})
    assert client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"], "itens": itens[:1]}).status_code == 422
    assert client.post("/api/parceiro/listas", headers=h[1], json={"data": "2026-11-04", "produto_ids": [produto["id"]]}).status_code == 422


def test_horarios_customizados_e_relatorio_vazio(ambiente):
    client, ctx, h, _ = ambiente
    assert client.patch("/api/parceiro/restaurante/horarios", headers=h[1], json={"horario_abertura": "07:00", "horario_fechamento": "12:00"}).status_code == 200
    assert client.patch("/api/parceiro/restaurante/horarios", headers=h[1], json={"horario_abertura": "13:00", "horario_fechamento": "12:00"}).status_code == 422
    _, lista = publicar(client, h, horario_abertura="08:30", horario_fechamento="10:30")
    assert datetime.fromisoformat(lista["horario_fechamento"]).minute == 30
    r = client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1]).json()["relatorio"]
    assert r["valor_total"] == 0 and r["itens"] == [] and "sem pedidos" in r["mensagem"]


def test_notificacao_nao_duplica_e_webhook_falha_sem_perder_aviso(ambiente, monkeypatch):
    client, ctx, h, _ = ambiente
    publicar(client, h)
    from app.application import notificacao_service
    monkeypatch.setattr(notificacao_service.settings, "NOTIFICATION_WEBHOOK_URL", "https://push.exemplo.test")
    def indisponivel(*args, **kwargs):
        raise OSError("offline")
    monkeypatch.setattr(notificacao_service, "urlopen", indisponivel)
    servico = ServicoNotificacao(ctx)
    servico.processar()
    servico.processar()
    assert len(client.get("/api/notificacoes", headers=h[3]).json()) == 1
    # Uma falha tem retentativa futura; chamadas imediatas não repetem o envio.
    assert ctx.notificacoes.pendentes_externos() == []


def test_pedidos_concorrentes_preservam_pedido_unico(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    barreira = Barrier(2)
    def pedir():
        from app.domain import PedidoAtivoExistenteError
        barreira.wait(timeout=5)
        try:
            ServicoCliente(ctx, lambda: FIXO).criar_pedido(3, lista["id"], {produto["id"]: 1})
            return "aceito"
        except PedidoAtivoExistenteError:
            return "duplicado"
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(pedir) for _ in range(2)]
        assert sorted(f.result(timeout=10) for f in futuros) == ["aceito", "duplicado"]
    assert len(ctx.pedidos.listar_por_usuario(3)) == 1


def test_fechamento_concorrente_nao_perde_pedido_no_relatorio(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    barreira = Barrier(2)
    restaurante = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao)
    def pedir():
        from app.domain import RegraDeNegocioError
        barreira.wait(timeout=5)
        try:
            ServicoCliente(ctx, lambda: FIXO).criar_pedido(3, lista["id"], {produto["id"]: 1})
            return True
        except RegraDeNegocioError as erro:
            assert erro.codigo == "lista_fechada"
            return False
    def fechar():
        barreira.wait(timeout=5)
        restaurante.fechar_lista(1, lista["id"])
    with ThreadPoolExecutor(max_workers=2) as executor:
        pedido = executor.submit(pedir)
        fechamento = executor.submit(fechar)
        aceito = pedido.result(timeout=10)
        fechamento.result(timeout=10)
    relatorio = restaurante.obter_relatorio(1, lista["id"])
    assert relatorio["total_pedidos"] == int(aceito)


def test_falha_de_gravacao_desfaz_pedido_e_itens(ambiente, monkeypatch):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    salvar = ctx.pedidos.salvar
    def falhar(pedido):
        salvar(pedido)
        raise RuntimeError("Falha depois de gravar os itens")
    monkeypatch.setattr(ctx.pedidos, "salvar", falhar)
    with pytest.raises(RuntimeError):
        ServicoCliente(ctx, lambda: FIXO).criar_pedido(3, lista["id"], {produto["id"]: 1})
    assert ctx.pedidos.listar_por_usuario(3) == []
    assert ctx.listas.obter_por_id(lista["id"]).pedidos == []


@pytest.mark.parametrize("disponivel", [True, False])
def test_excluir_produto_proprio_sem_vinculos_e_preservar_outro_restaurante(ambiente, disponivel):
    client, ctx, h, _ = ambiente
    produto = client.post("/api/parceiro/produtos", headers=h[1],
                          json={"nome": "Produto para excluir", "preco": "10.00", "disponivel": disponivel}).json()
    outro = client.post("/api/parceiro/produtos", headers=h[2], json={"nome": "Outro produto", "preco": "20.00"}).json()
    caminho = f"/api/parceiro/produtos/{produto['id']}"
    assert client.delete(caminho).status_code == 401
    assert client.delete(caminho, headers=h[3]).status_code == 403
    assert client.delete(caminho, headers=h[2]).status_code == 403
    assert ctx.produtos.obter_por_id(produto["id"]) is not None
    resultado = client.delete(caminho, headers=h[1])
    assert resultado.status_code == 200, resultado.text
    assert "excluído com sucesso" in resultado.json()["mensagem"]
    assert ctx.produtos.obter_por_id(produto["id"]) is None
    assert client.get("/api/parceiro/produtos", headers=h[1]).json() == []
    assert client.get("/api/parceiro/produtos", headers=h[2]).json() == [outro]
    assert client.delete(caminho, headers=h[1]).status_code == 404
    assert client.patch(caminho, headers=h[1], json={"nome": "Não pode reaparecer"}).status_code == 404
    novo = client.post("/api/parceiro/produtos", headers=h[1], json={"nome": "Novo produto", "preco": "15.00"}).json()
    assert novo["id"] > produto["id"]


@pytest.mark.parametrize("cenario", ["lista_aberta", "lista_fechada", "pedido_ativo", "pedido_cancelado"])
def test_produto_vinculado_nao_pode_ser_excluido_e_preserva_historico(ambiente, cenario):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = None
    if cenario.startswith("pedido_"):
        pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                              "itens": [{"produto_id": produto["id"], "quantidade": 2}]}).json()
        if cenario == "pedido_cancelado":
            assert client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[3]).status_code == 200
    if cenario == "lista_fechada":
        assert client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1]).status_code == 200
    resposta = client.delete(f"/api/parceiro/produtos/{produto['id']}", headers=h[1])
    assert resposta.status_code == 409, resposta.text
    assert resposta.json()["codigo"] == "produto_em_uso"
    assert "Desativar" in resposta.json()["detail"]
    assert ctx.produtos.obter_por_id(produto["id"]).disponivel
    assert produto["id"] in ctx.listas.obter_por_id(lista["id"]).produtos
    listas = client.get("/api/parceiro/listas", headers=h[1]).json()
    assert listas[0]["produtos"][0]["id"] == produto["id"]
    if pedido is not None:
        preservado = client.get(f"/api/pedidos/{pedido['id']}", headers=h[3])
        assert preservado.status_code == 200
        assert Decimal(str(preservado.json()["valor_total"])) == Decimal("51.00")
        assert preservado.json()["status"] == ("CANCELADO" if cenario == "pedido_cancelado" else "ATIVO")
    client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1])
    relatorio = client.get(f"/api/parceiro/listas/{lista['id']}/relatorio", headers=h[1]).json()
    assert relatorio["total_pedidos"] == int(cenario == "pedido_ativo")


def test_falha_na_exclusao_desfaz_remocao_do_produto(ambiente, monkeypatch):
    client, ctx, h, _ = ambiente
    produto = client.post("/api/parceiro/produtos", headers=h[1], json={"nome": "Produto", "preco": "10.00"}).json()
    excluir = ctx.produtos.excluir
    def falhar(produto_id):
        assert excluir(produto_id)
        raise RuntimeError("Falha após excluir o produto")
    monkeypatch.setattr(ctx.produtos, "excluir", falhar)
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao)
    with pytest.raises(RuntimeError):
        servico.excluir_produto(1, produto["id"])
    assert ctx.produtos.obter_por_id(produto["id"]) is not None


def test_excluir_e_publicar_concorrentes_nao_deixam_lista_sem_produto(ambiente):
    client, ctx, h, _ = ambiente
    produto = client.post("/api/parceiro/produtos", headers=h[1], json={"nome": "Produto", "preco": "10.00"}).json()
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao)
    barreira = Barrier(2)
    def excluir():
        from app.domain import RegraDeNegocioError
        barreira.wait(timeout=5)
        try:
            servico.excluir_produto(1, produto["id"])
            return True
        except RegraDeNegocioError as erro:
            assert erro.codigo == "produto_em_uso"
            return False
    def criar_lista():
        from app.domain import ValidacaoDeDominioError
        barreira.wait(timeout=5)
        try:
            servico.criar_lista_diaria(1, FIXO.date(), [produto["id"]], FIXO)
            return True
        except ValidacaoDeDominioError as erro:
            assert erro.codigo == "produto_nao_encontrado"
            return False
    with ThreadPoolExecutor(max_workers=2) as executor:
        exclusao = executor.submit(excluir)
        publicacao = executor.submit(criar_lista)
        excluido, publicado = exclusao.result(timeout=10), publicacao.result(timeout=10)
    assert excluido != publicado
    listas = ctx.listas.listar_por_restaurante(1)
    assert len(listas) == int(publicado)
    if publicado:
        assert produto["id"] in listas[0].produtos
        assert ctx.produtos.obter_por_id(produto["id"]) is not None
    else:
        assert ctx.produtos.obter_por_id(produto["id"]) is None


@pytest.mark.parametrize("lista_fechada", [False, True])
def test_parceiro_conclui_retirada_e_preserva_pedido_e_relatorio(ambiente, lista_fechada):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                          "itens": [{"produto_id": produto["id"], "quantidade": 2}]}).json()
    # Compara com a leitura persistida, que já contém os IDs gerados pelo banco.
    pedido = client.get(f"/api/pedidos/{pedido['id']}", headers=h[3]).json()
    if lista_fechada:
        client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1])
    caminho = f"/api/parceiro/listas/{lista['id']}/pedidos"
    antes = client.get(caminho, headers=h[1])
    assert antes.status_code == 200
    assert antes.json()[0]["cliente"] == "Usuário 3"
    assert not antes.json()[0]["concluido"]
    assert "senha_hash" not in antes.text and "email" not in antes.text
    resposta = client.post(f"{caminho}/{pedido['id']}/retirada", headers=h[1])
    assert resposta.status_code == 200, resposta.text
    concluido = resposta.json()
    assert concluido["status"] == "ATIVO"
    assert concluido["status_retirada"] == "RETIRADO"
    assert concluido["concluido"] and not concluido["pode_cancelar"]
    assert concluido["itens"] == pedido["itens"]  # inclusive IDs de persistência
    assert concluido["valor_total"] == pedido["valor_total"]
    assert client.post(f"{caminho}/{pedido['id']}/retirada", headers=h[1]).json() == concluido
    assert client.get(f"/api/pedidos/{pedido['id']}", headers=h[3]).json()["concluido"]
    assert client.get(caminho, headers=h[1]).json()[0]["concluido"]
    if lista_fechada:
        assert client.post(f"/api/parceiro/listas/{lista['id']}/abrir", headers=h[1]).status_code == 200
    cancelamento = client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[3])
    assert cancelamento.status_code == 409
    assert cancelamento.json()["codigo"] == "pedido_ja_retirado"
    assert client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                       "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).status_code == 409
    client.post(f"/api/parceiro/listas/{lista['id']}/fechar", headers=h[1])
    relatorio = client.get(f"/api/parceiro/listas/{lista['id']}/relatorio", headers=h[1]).json()
    assert relatorio["total_pedidos"] == 1
    assert Decimal(str(relatorio["valor_total"])) == Decimal("51.00")
    assert relatorio["itens"][0]["quantidade"] == 2


def test_consulta_e_confirmacao_de_retirada_respeitam_papel_restaurante_e_lista(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                          "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).json()
    caminho = f"/api/parceiro/listas/{lista['id']}/pedidos"
    retirada = f"{caminho}/{pedido['id']}/retirada"
    assert client.get(caminho).status_code == 401
    assert client.post(retirada).status_code == 401
    for uid in (3, 4, 2):
        assert client.get(caminho, headers=h[uid]).status_code == 403
        assert client.post(retirada, headers=h[uid]).status_code == 403
    _, outra_lista = publicar(client, h)
    assert client.post(f"/api/parceiro/listas/{outra_lista['id']}/pedidos/{pedido['id']}/retirada", headers=h[1]).status_code == 404
    assert client.post(f"{caminho}/999999/retirada", headers=h[1]).status_code == 404
    assert client.get("/api/parceiro/listas/999999/pedidos", headers=h[1]).status_code == 404
    assert client.post(f"/api/parceiro/listas/999999/pedidos/{pedido['id']}/retirada", headers=h[1]).status_code == 404
    assert ctx.pedidos.obter_por_id(pedido["id"]).status_retirada.value == "PENDENTE"


def test_pedido_cancelado_nao_pode_ser_retirado(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                          "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).json()
    client.post(f"/api/pedidos/{pedido['id']}/cancelar", headers=h[3])
    caminho = f"/api/parceiro/listas/{lista['id']}/pedidos"
    resposta = client.post(f"{caminho}/{pedido['id']}/retirada", headers=h[1])
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "pedido_cancelado"
    registro = client.get(caminho, headers=h[1]).json()[0]
    assert registro["status"] == "CANCELADO" and registro["status_retirada"] == "PENDENTE"
    assert not registro["concluido"]


def test_falha_ao_salvar_retirada_preserva_estado_anterior(ambiente, monkeypatch):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                          "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).json()
    pedido = client.get(f"/api/pedidos/{pedido['id']}", headers=h[3]).json()
    salvar = ctx.pedidos.salvar_retirada
    def falhar(pedido):
        salvar(pedido)
        raise RuntimeError("Falha depois de salvar a retirada")
    monkeypatch.setattr(ctx.pedidos, "salvar_retirada", falhar)
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas,
                                ctx.transacao, pedidos=ctx.pedidos)
    with pytest.raises(RuntimeError):
        servico.confirmar_retirada(1, lista["id"], pedido["id"])
    preservado = client.get(f"/api/pedidos/{pedido['id']}", headers=h[3]).json()
    assert preservado["status_retirada"] == "PENDENTE" and not preservado["concluido"]
    assert preservado["itens"] == pedido["itens"]


def test_retirada_e_cancelamento_concorrentes_nao_produzem_estados_incompativeis(ambiente):
    client, ctx, h, _ = ambiente
    produto, lista = publicar(client, h)
    pedido = client.post("/api/pedidos", headers=h[3], json={"lista_id": lista["id"],
                          "itens": [{"produto_id": produto["id"], "quantidade": 1}]}).json()
    servico = ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas,
                                ctx.transacao, pedidos=ctx.pedidos)
    barreira = Barrier(2)
    def operar(retirar):
        from app.domain import RegraDeNegocioError
        barreira.wait(timeout=5)
        try:
            if retirar:
                servico.confirmar_retirada(1, lista["id"], pedido["id"])
            else:
                ServicoCliente(ctx, lambda: FIXO).cancelar_pedido(3, pedido["id"])
            return "sucesso"
        except RegraDeNegocioError as erro:
            return erro.codigo
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(operar, retirar) for retirar in (False, True)]
        resultados = [f.result(timeout=10) for f in futuros]
    assert resultados.count("sucesso") == 1
    assert set(resultados) <= {"sucesso", "pedido_cancelado", "pedido_ja_retirado"}
    registro = ctx.pedidos.obter_por_id(pedido["id"])
    assert (registro.status.value, registro.status_retirada.value) in {
        ("CANCELADO", "PENDENTE"), ("ATIVO", "RETIRADO")}
