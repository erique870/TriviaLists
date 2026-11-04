from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from app.application.ports import RepositorioUsuario
from app.application.repositories import RepositorioUsuariosEmMemoria
from app.core.security import TokenExpiradoError, TokenInvalidoError, decodificar_token_acesso
from app.domain.enums import PapelUsuario
from app.domain.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_usuario_repo(request: Request) -> RepositorioUsuario:
    """Injeta a implementação do repositório de usuários configurado no app."""
    if hasattr(request.app.state, "contexto"):
        return request.app.state.contexto.usuarios
    if hasattr(request.app.state, "repositorio_usuario"):
        return request.app.state.repositorio_usuario
    if hasattr(request.app.state, "db"):
        from app.infrastructure.postgres import RepositorioUsuarioPostgres
        return RepositorioUsuarioPostgres(request.app.state.db)
    if not hasattr(request.app.state, "_fallback_user_repo"):
        request.app.state._fallback_user_repo = RepositorioUsuariosEmMemoria()
    return request.app.state._fallback_user_repo


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    usuarios: Annotated[RepositorioUsuario, Depends(get_usuario_repo)],
) -> Usuario:
    """Extrai e valida o token JWT, retornando a entidade de domínio Usuario."""
    credenciais_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de autenticação inválido ou ausente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decodificar_token_acesso(token)
        usuario_id_str = payload.get("sub")
        if usuario_id_str is None:
            raise credenciais_exception
        usuario_id = int(usuario_id_str)
    except TokenExpiradoError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão expirada. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (TokenInvalidoError, ValueError, TypeError):
        raise credenciais_exception

    usuario = usuarios.obter_por_id(usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário associado ao token não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def require_aluno(
    usuario: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Garante que o usuário autenticado possui o papel ALUNO (RN05)."""
    if usuario.papel != PapelUsuario.ALUNO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação permitida apenas para alunos.",
        )
    return usuario


def require_parceiro(
    usuario: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Garante que o usuário autenticado possui o papel PARCEIRO vinculado a um restaurante (RN05)."""
    if usuario.papel != PapelUsuario.PARCEIRO or usuario.restaurante_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação permitida apenas para parceiros comerciais cadastrados.",
        )
    return usuario
