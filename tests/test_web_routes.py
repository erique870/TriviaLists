import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_pagina_principal_index_html(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Trivialists" in response.text
    assert "login-email" in response.text
    assert "cad-nome" in response.text


def test_pagina_login_rota_alternativa(client: TestClient):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Trivialists" in response.text


def test_pagina_aluno_html(client: TestClient):
    response = client.get("/aluno")
    assert response.status_code == 200
    assert "Área do Aluno" in response.text
    assert "btn-logout" in response.text


def test_pagina_parceiro_html(client: TestClient):
    response = client.get("/parceiro")
    assert response.status_code == 200
    assert "Painel do Restaurante" in response.text
    assert "btn-logout" in response.text


def test_arquivos_estaticos_css_e_js(client: TestClient):
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert "--color-main" in css_res.text

    js_auth = client.get("/static/js/auth.js")
    assert js_auth.status_code == 200
    assert "fetch('/auth/login'" in js_auth.text

    js_sess = client.get("/static/js/session.js")
    assert js_sess.status_code == 200
    assert "CHAVE_TOKEN" in js_sess.text
