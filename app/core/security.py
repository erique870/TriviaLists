from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import settings


class TokenInvalidoError(Exception):
    """Exceção levantada quando o token possui formato ou assinatura inválida."""


class TokenExpiradoError(Exception):
    """Exceção levantada quando o token de autenticação está expirado."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("utf-8"))


def gerar_hash_senha(senha: str) -> str:
    """Gera hash criptográfico usando scrypt (RFC 7914, nativo da stdlib do Python 3.8+)."""
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(
        senha.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
    )
    return f"scrypt${salt}${key.hex()}"


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Verifica senha com comparação em tempo constante contra scrypt e hashes legados."""
    try:
        if senha_hash.startswith("scrypt$"):
            _, salt, key_hex = senha_hash.split("$")
            computed = hashlib.scrypt(
                senha_plana.encode("utf-8"),
                salt=salt.encode("utf-8"),
                n=16384,
                r=8,
                p=1,
            )
            return hmac.compare_digest(computed.hex(), key_hex)
        elif senha_hash.startswith("$argon2"):
            try:
                from argon2 import PasswordHasher
                return PasswordHasher().verify(senha_hash, senha_plana)
            except Exception:
                return False
        return False
    except Exception:
        return False


def criar_token_acesso(dados: dict[str, Any], expira_em: timedelta | None = None) -> str:
    """Cria um token de acesso JWT (HS256) compatível com padrões web usando puramente a stdlib."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = dict(dados)
    agora = int(time.time())
    payload.setdefault("iat", agora)

    if expira_em is not None:
        payload["exp"] = agora + int(expira_em.total_seconds())
    else:
        payload["exp"] = agora + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    h_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    msg = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    s_b64 = _b64url_encode(sig)
    return f"{h_b64}.{p_b64}.{s_b64}"


def decodificar_token_acesso(token: str) -> dict[str, Any]:
    """Decodifica e valida assinatura e expiração do JWT."""
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenInvalidoError("Formato de token inválido")

    h_b64, p_b64, s_b64 = parts
    msg = f"{h_b64}.{p_b64}".encode("utf-8")
    expected_sig = hmac.new(settings.JWT_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()

    try:
        actual_sig = _b64url_decode(s_b64)
    except Exception as e:
        raise TokenInvalidoError("Assinatura com codificação inválida") from e

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise TokenInvalidoError("Assinatura do token não confere")

    try:
        payload = json.loads(_b64url_decode(p_b64).decode("utf-8"))
    except Exception as e:
        raise TokenInvalidoError("Payload JSON inválido") from e

    if "exp" in payload and time.time() > payload["exp"]:
        raise TokenExpiradoError("Token expirado")

    return payload
