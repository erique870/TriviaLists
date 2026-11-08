import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import PapelUsuario

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CadastroAlunoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    nome: str = Field(..., min_length=2, max_length=150, description="Nome completo do aluno")
    email: str = Field(..., description="E-mail válido do aluno")
    telefone: str = Field(..., min_length=8, max_length=20, description="Telefone ou WhatsApp para contato")
    senha: str = Field(..., min_length=6, max_length=100, description="Senha de acesso")

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Formato de e-mail inválido")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., description="E-mail de acesso cadastrado")
    senha: str = Field(..., min_length=1, description="Senha de acesso")

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_REGEX.match(v):
            raise ValueError("Formato de e-mail inválido")
        return v


class UsuarioOut(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str
    papel: PapelUsuario
    restaurante_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
