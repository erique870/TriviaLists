from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.ports import RepositorioUsuario
from app.core.security import criar_token_acesso, gerar_hash_senha, verificar_senha
from app.domain.enums import PapelUsuario
from app.domain.usuario import Usuario
from app.routers.deps import get_current_user, get_usuario_repo
from app.schemas.auth import CadastroAlunoRequest, LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica usuário e retorna JWT de sessão",
    description="Permite que Alunos e Parceiros acessem suas áreas exclusivas gerando token de 7 dias.",
)
def login(
    dados: LoginRequest,
    usuarios: Annotated[RepositorioUsuario, Depends(get_usuario_repo)],
) -> TokenResponse:
    usuario = usuarios.obter_por_email(dados.email)
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = {
        "sub": str(usuario.id),
        "email": usuario.email,
        "papel": usuario.papel.value,
        "restaurante_id": usuario.restaurante_id,
    }
    token = criar_token_acesso(claims)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        usuario=UsuarioOut(
            id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            telefone=usuario.telefone,
            papel=usuario.papel,
            restaurante_id=usuario.restaurante_id,
        ),
    )


@router.post(
    "/cadastro",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Fluxo alternativo FA01: Cadastra um novo aluno no sistema",
)
def cadastrar_aluno(
    dados: CadastroAlunoRequest,
    usuarios: Annotated[RepositorioUsuario, Depends(get_usuario_repo)],
) -> TokenResponse:
    existente = usuarios.obter_por_email(dados.email)
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta cadastrada com este e-mail.",
        )

    hash_senha = gerar_hash_senha(dados.senha)
    novo_usuario = Usuario(
        id=0,
        nome=dados.nome.strip(),
        email=dados.email.strip().lower(),
        senha_hash=hash_senha,
        telefone=dados.telefone.strip(),
        papel=PapelUsuario.ALUNO,
        restaurante_id=None,
    )
    usuario_criado = usuarios.salvar(novo_usuario)

    claims = {
        "sub": str(usuario_criado.id),
        "email": usuario_criado.email,
        "papel": usuario_criado.papel.value,
        "restaurante_id": None,
    }
    token = criar_token_acesso(claims)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        usuario=UsuarioOut(
            id=usuario_criado.id,
            nome=usuario_criado.nome,
            email=usuario_criado.email,
            telefone=usuario_criado.telefone,
            papel=usuario_criado.papel,
            restaurante_id=None,
        ),
    )


@router.get(
    "/me",
    response_model=UsuarioOut,
    summary="Retorna os dados do usuário autenticado a partir do token",
)
def obter_usuario_logado(
    usuario_atual: Annotated[Usuario, Depends(get_current_user)],
) -> UsuarioOut:
    return UsuarioOut(
        id=usuario_atual.id,
        nome=usuario_atual.nome,
        email=usuario_atual.email,
        telefone=usuario_atual.telefone,
        papel=usuario_atual.papel,
        restaurante_id=usuario_atual.restaurante_id,
    )
