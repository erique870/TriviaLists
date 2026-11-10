from datetime import timedelta
import pytest

from app.core.security import (
    TokenExpiradoError,
    TokenInvalidoError,
    criar_token_acesso,
    decodificar_token_acesso,
    gerar_hash_senha,
    verificar_senha,
)


def test_gerar_hash_senha_gera_hashes_com_sal_diferentes():
    senha = "MinhaSenhaForte@123"
    hash1 = gerar_hash_senha(senha)
    hash2 = gerar_hash_senha(senha)

    assert hash1 != hash2
    assert hash1.startswith("scrypt$")


def test_verificar_senha_valida_corretamente():
    senha = "SenhaCorreta@2026"
    hash_senha = gerar_hash_senha(senha)

    assert verificar_senha(senha, hash_senha) is True
    assert verificar_senha("SenhaIncorreta", hash_senha) is False
    assert verificar_senha("", hash_senha) is False
    assert verificar_senha(senha, "hash_invalido_qualquer") is False


def test_criar_e_decodificar_token_jwt():
    payload = {
        "sub": "42",
        "email": "cliente@exemplo.com",
        "papel": "CLIENTE",
        "restaurante_id": None,
    }
    token = criar_token_acesso(payload, expira_em=timedelta(minutes=30))

    dados = decodificar_token_acesso(token)
    assert dados["sub"] == "42"
    assert dados["email"] == "cliente@exemplo.com"
    assert dados["papel"] == "CLIENTE"
    assert dados["restaurante_id"] is None
    assert "exp" in dados
    assert "iat" in dados


def test_token_jwt_expirado_falha():
    payload = {"sub": "1"}
    token = criar_token_acesso(payload, expira_em=timedelta(seconds=-1))

    with pytest.raises(TokenExpiradoError):
        decodificar_token_acesso(token)


def test_token_jwt_invalido_falha():
    with pytest.raises(TokenInvalidoError):
        decodificar_token_acesso("token.totalmente.invalido")
