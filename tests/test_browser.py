"""Fluxo real das telas; opt-in com RUN_BROWSER_TESTS=1 e Playwright instalado."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Teste de navegador opcional.")


def test_parceiro_publica_cliente_pede_cancela_e_parceiro_fecha():
    playwright = pytest.importorskip("playwright.sync_api")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        porta = sock.getsockname()[1]
    url = f"http://127.0.0.1:{porta}"
    env = dict(os.environ, DATABASE_URL="", APP_DEMO="true", WORKER_INTERVAL_SECONDS="1", NOTIFICATION_WEBHOOK_URL="")
    processo = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(porta)],
                                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            if processo.poll() is not None:
                pytest.fail("O servidor web encerrou antes de iniciar.")
            try:
                with urlopen(url + "/health", timeout=1):
                    break
            except OSError:
                time.sleep(.1)
        else:
            pytest.fail("O servidor web não iniciou.")
        with playwright.sync_playwright() as p:
            chrome = os.getenv("CHROME_PATH") or shutil.which("google-chrome")
            browser = p.chromium.launch(executable_path=chrome, headless=True, args=["--no-sandbox"])
            erros = []
            parceiro = browser.new_page(viewport={"width": 1280, "height": 900})
            cliente = browser.new_page(viewport={"width": 390, "height": 844})
            for pagina in (parceiro, cliente):
                pagina.on("pageerror", lambda erro: erros.append(str(erro)))
            def login(pagina, email, caminho):
                pagina.goto(url)
                pagina.locator("#login-email").fill(email)
                pagina.locator("#login-senha").fill("demo12345")
                pagina.locator("#btn-entrar").click()
                pagina.wait_for_url(url + caminho)
                playwright.expect(pagina.locator("#user-nome")).not_to_have_text("Carregando...")

            login(parceiro, "salsalito@exemplo.com", "/parceiro")
            parceiro.locator("#produto-nome").fill("Produto para excluir")
            parceiro.locator("#produto-preco").fill("10.00")
            parceiro.locator("#form-produto [type=submit]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("Produto salvo")
            parceiro.locator("#produtos [data-editar]").click()
            parceiro.once("dialog", lambda dialogo: dialogo.dismiss())
            parceiro.locator("#produtos [data-excluir]").click()
            playwright.expect(parceiro.locator("#produtos [data-excluir]")).to_have_count(1)
            parceiro.once("dialog", lambda dialogo: dialogo.accept())
            parceiro.locator("#produtos [data-excluir]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("Produto excluído com sucesso")
            playwright.expect(parceiro.locator("#produtos [data-excluir]")).to_have_count(0)
            playwright.expect(parceiro.locator("#lista-produtos input")).to_have_count(0)
            playwright.expect(parceiro.locator("#produto-id")).to_have_value("")
            playwright.expect(parceiro.locator("#produto-nome")).to_have_value("")
            parceiro.locator("#produto-nome").fill("Quentinha do teste")
            parceiro.locator("#produto-preco").fill("25.50")
            parceiro.locator("#produto-descricao").fill("Arroz e frango")
            parceiro.locator("#form-produto [type=submit]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("Produto salvo")
            parceiro.locator("#lista-produtos input").check()
            # O teste independe do horário de execução: usa uma janela de 24h local.
            parceiro.locator("#lista-abertura").fill("00:00")
            parceiro.locator("#lista-fechamento").fill("23:59")
            parceiro.locator("#form-lista [type=submit]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("publicado!")
            login(cliente, "cliente@impatech.edu.br", "/cliente")
            playwright.expect(cliente.locator("#notificacoes")).to_contain_text("publicou o cardápio")
            cliente.locator("#listas input[data-produto]").fill("2")
            cliente.locator("#listas [type=submit]").click()
            playwright.expect(cliente.locator("#app-alert")).to_contain_text("confirmado!")
            playwright.expect(cliente.locator("#pedidos")).to_contain_text("51,00")
            cliente.locator("[data-cancelar]").click()
            playwright.expect(cliente.locator("#app-alert")).to_contain_text("cancelado com sucesso")
            cliente.locator("#listas input[data-produto]").fill("1")
            cliente.locator("#listas [type=submit]").click()
            playwright.expect(cliente.locator("#app-alert")).to_contain_text("confirmado!")
            parceiro.locator('[data-acao="fechar"]').click()
            playwright.expect(parceiro.locator("#relatorio")).to_contain_text("25,50")
            playwright.expect(parceiro.locator("#relatorio")).to_contain_text("1 pedido(s)")
            parceiro.locator('[data-acao="pedidos"]').click()
            playwright.expect(parceiro.locator("#pedidos-retirada")).to_contain_text("Cliente de demonstração")
            playwright.expect(parceiro.locator("[data-confirmar-retirada]")).to_have_count(1)
            parceiro.locator("[data-confirmar-retirada]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("retirada confirmada")
            playwright.expect(parceiro.locator("#pedidos-retirada")).to_contain_text("CONCLUÍDO")
            playwright.expect(parceiro.locator("[data-confirmar-retirada]")).to_have_count(0)
            playwright.expect(parceiro.locator("#relatorio")).to_contain_text("25,50")
            parceiro.once("dialog", lambda dialogo: dialogo.accept())
            parceiro.locator("#produtos [data-excluir]").click()
            playwright.expect(parceiro.locator("#app-alert")).to_contain_text("vinculado a listas ou pedidos")
            playwright.expect(parceiro.locator("#produtos [data-excluir]")).to_have_count(1)
            playwright.expect(parceiro.locator("#relatorio")).to_contain_text("25,50")
            cliente.locator("#atualizar").click()
            playwright.expect(cliente.locator("#listas")).to_contain_text("Nenhum restaurante")
            playwright.expect(cliente.locator("#pedidos")).to_contain_text("CONCLUÍDO")
            playwright.expect(cliente.locator("#pedidos")).to_contain_text("RETIRADO")
            playwright.expect(cliente.locator("[data-cancelar]")).to_have_count(0)
            assert cliente.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            # A expiração é validada pelo servidor e leva de volta ao acesso.
            cliente.evaluate("localStorage.setItem('trivialists_token', 'token.invalido.assinatura')")
            cliente.reload()
            cliente.wait_for_url(url + "/?msg=login_necessario")
            assert not erros, erros
            artefatos = os.getenv("BROWSER_ARTIFACT_DIR")
            if artefatos:
                Path(artefatos).mkdir(parents=True, exist_ok=True)
                parceiro.screenshot(path=str(Path(artefatos) / "relatorio.png"), full_page=True)
            browser.close()
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()
