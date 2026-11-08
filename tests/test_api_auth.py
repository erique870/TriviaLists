from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.application.repositories import RepositorioUsuariosEmMemoria
from app.core.security import criar_token_acesso, gerar_hash_senha
from app.domain.enums import PapelUsuario
from app.domain.usuario import Usuario
from app.main import app
from app.routers.deps import get_usuario_repo, require_aluno, require_parceiro


# Rotas simuladas para testar guards de autorização por papel (RN05)
@app.get("/test/aluno-only")
def rota_apenas_aluno(usuario: Usuario = pytest.importorskip("fastapi").Depends(require_aluno)):
    return {"msg": f"Bem-vindo aluno {usuario.nome}"}


@app.get("/test/parceiro-only")
def rota_apenas_parceiro(usuario: Usuario = pytest.importorskip("fastapi").Depends(require_parceiro)):
    return {"msg": f"Bem-vindo parceiro do restaurante {usuario.restaurante_id}"}


@pytest.fixture
def repo_memoria() -> RepositorioUsuariosEmMemoria:
    usuario_aluno = Usuario(
        id=1,
        nome="Erique Aluno",
        email="erique@impatech.edu.br",
        senha_hash=gerar_hash_senha("SenhaAluno123"),
        telefone="21999998888",
        papel=PapelUsuario.ALUNO,
        restaurante_id=None,
    )
    usuario_parceiro = Usuario(
        id=2,
        nome="Gerente Salsalito",
        email="salsalito@teste.com",
        senha_hash=gerar_hash_senha("SenhaParceiro123"),
        telefone="21988887777",
        papel=PapelUsuario.PARCEIRO,
        restaurante_id=1,
    )
    return RepositorioUsuariosEmMemoria([usuario_aluno, usuario_parceiro])


@pytest.fixture
def client(repo_memoria: RepositorioUsuariosEmMemoria) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_usuario_repo] = lambda: repo_memoria
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_login_aluno_sucesso(client: TestClient):
    payload = {
        "email": "erique@impatech.edu.br",
        "senha": "SenhaAluno123",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200

    dados = response.json()
    assert "access_token" in dados
    assert dados["token_type"] == "bearer"
    assert dados["usuario"]["email"] == "erique@impatech.edu.br"
    assert dados["usuario"]["papel"] == "ALUNO"
    assert dados["usuario"]["restaurante_id"] is None


def test_login_parceiro_sucesso(client: TestClient):
    payload = {
        "email": "salsalito@teste.com",
        "senha": "SenhaParceiro123",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200

    dados = response.json()
    assert dados["usuario"]["papel"] == "PARCEIRO"
    assert dados["usuario"]["restaurante_id"] == 1


def test_login_credenciais_incorretas(client: TestClient):
    payload = {
        "email": "erique@impatech.edu.br",
        "senha": "SenhaTotalmenteErrada",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "E-mail ou senha incorretos." in response.json()["detail"]


def test_login_usuario_inexistente(client: TestClient):
    payload = {
        "email": "inexistente@impatech.edu.br",
        "senha": "qualquer_senha",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "E-mail ou senha incorretos." in response.json()["detail"]


def test_cadastro_aluno_sucesso_fa01(client: TestClient):
    payload = {
        "nome": "Novo Aluno Impatech",
        "email": "novato@impatech.edu.br",
        "telefone": "21977776666",
        "senha": "NovaSenhaSegura123",
    }
    response = client.post("/auth/cadastro", json=payload)
    assert response.status_code == 201

    dados = response.json()
    assert "access_token" in dados
    assert dados["usuario"]["nome"] == "Novo Aluno Impatech"
    assert dados["usuario"]["email"] == "novato@impatech.edu.br"
    assert dados["usuario"]["papel"] == "ALUNO"
    assert dados["usuario"]["restaurante_id"] is None

    # Tenta logar com a conta recém criada
    login_res = client.post(
        "/auth/login",
        json={"email": "novato@impatech.edu.br", "senha": "NovaSenhaSegura123"},
    )
    assert login_res.status_code == 200


def test_cadastro_aluno_email_duplicado_conflito(client: TestClient):
    payload = {
        "nome": "Tentativa Duplicada",
        "email": "erique@impatech.edu.br",
        "telefone": "21900001111",
        "senha": "OutraSenha123",
    }
    response = client.post("/auth/cadastro", json=payload)
    assert response.status_code == 409
    assert "Já existe uma conta" in response.json()["detail"]


def test_me_retorna_usuario_autenticado(client: TestClient):
    token = criar_token_acesso({"sub": "1", "email": "erique@impatech.edu.br", "papel": "ALUNO"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200

    dados = response.json()
    assert dados["id"] == 1
    assert dados["email"] == "erique@impatech.edu.br"
    assert dados["papel"] == "ALUNO"


def test_me_sem_token_retorna_401(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_token_expirado_retorna_401(client: TestClient):
    token_expirado = criar_token_acesso(
        {"sub": "1", "email": "erique@impatech.edu.br"},
        expira_em=timedelta(seconds=-10),
    )
    headers = {"Authorization": f"Bearer {token_expirado}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Sessão expirada." in response.json()["detail"]


def test_me_token_malformado_retorna_401(client: TestClient):
    headers = {"Authorization": "Bearer token.completamente.errado"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Token de autenticação inválido" in response.json()["detail"]


def test_endpoint_exclusivo_aluno_bloqueia_parceiro(client: TestClient):
    token_parceiro = criar_token_acesso({"sub": "2", "email": "salsalito@teste.com", "papel": "PARCEIRO"})
    headers = {"Authorization": f"Bearer {token_parceiro}"}

    response = client.get("/test/aluno-only", headers=headers)
    assert response.status_code == 403
    assert "apenas para alunos" in response.json()["detail"]


def test_endpoint_exclusivo_parceiro_bloqueia_aluno(client: TestClient):
    token_aluno = criar_token_acesso({"sub": "1", "email": "erique@impatech.edu.br", "papel": "ALUNO"})
    headers = {"Authorization": f"Bearer {token_aluno}"}

    response = client.get("/test/parceiro-only", headers=headers)
    assert response.status_code == 403
    assert "apenas para parceiros comerciais" in response.json()["detail"]


def test_erro_de_validacao_devolve_detail_em_texto(client: TestClient):
    """O 422 precisa ter `detail` em texto, como os demais handlers do app."""
    resposta = client.post("/auth/cadastro", json={
        "nome": "Carlos Silva", "email": "a@b", "telefone": "1", "senha": "senha123",
    })

    assert resposta.status_code == 422
    detalhe = resposta.json()["detail"]
    assert isinstance(detalhe, str), (
        f"detail veio como {type(detalhe).__name__}; o frontend o escreve direto na "
        f"tela e uma lista virar texto produz '[object Object]'."
    )
    assert "e-mail inválido" in detalhe
    assert "Telefone precisa de ao menos 8 caracteres" in detalhe


def test_erro_de_validacao_no_login_tambem_e_texto(client: TestClient):
    resposta = client.post("/auth/login", json={"email": "a@b", "senha": "x"})

    assert resposta.status_code == 422
    assert isinstance(resposta.json()["detail"], str)


def test_mensagens_de_validacao_saem_em_portugues(client: TestClient):
    resposta = client.post("/auth/cadastro", json={
        "nome": "A", "email": "a@b", "telefone": "1", "senha": "123",
    })

    assert resposta.status_code == 422
    assert resposta.json()["detail"] == (
        "Nome precisa de ao menos 2 caracteres; "
        "Formato de e-mail inválido; "
        "Telefone precisa de ao menos 8 caracteres; "
        "Senha precisa de ao menos 6 caracteres"
    )


def test_campo_ausente_e_campo_proibido_tem_mensagem_propria(client: TestClient):
    vazio = client.post("/auth/cadastro", json={})
    assert vazio.json()["detail"] == (
        "Nome é obrigatório; E-mail é obrigatório; "
        "Telefone é obrigatório; Senha é obrigatório"
    )

    extra = client.post("/auth/cadastro", json={
        "nome": "Carlos Silva", "email": "carlos@impatech.edu.br",
        "telefone": "21999998888", "senha": "senha123", "papel": "PARCEIRO",
    })
    assert extra.json()["detail"] == "Papel não é aceito neste formulário"
