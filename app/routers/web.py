from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Frontend Web"])

BASE_PUBLIC_DIR = Path(__file__).resolve().parent.parent.parent / "public"


@router.get("/", response_class=FileResponse, summary="Página Principal de Acesso (Login / Cadastro)")
async def index_page() -> FileResponse:
    return FileResponse(BASE_PUBLIC_DIR / "index.html")


@router.get("/login", response_class=FileResponse, summary="Página de Login")
async def login_page() -> FileResponse:
    return FileResponse(BASE_PUBLIC_DIR / "index.html")


@router.get("/cliente", response_class=FileResponse, summary="Interface Web do Cliente")
async def cliente_page() -> FileResponse:
    return FileResponse(BASE_PUBLIC_DIR / "cliente.html")


@router.get("/parceiro", response_class=FileResponse, summary="Interface Web do Parceiro")
async def parceiro_page() -> FileResponse:
    return FileResponse(BASE_PUBLIC_DIR / "parceiro.html")
