"""Dados descartáveis, disponíveis somente com APP_DEMO=true sem DATABASE_URL."""

from datetime import time

from app.core.security import gerar_hash_senha
from app.domain import PapelUsuario, Restaurante, TipoCardapio, Usuario


def carregar_demo(ctx):
    senha_hash = gerar_hash_senha("demo12345")
    for rid, nome, slug, tipo in [(1, "Salsalito", "salsalito", TipoCardapio.VARIAVEL),
                                  (2, "Pilograma", "pilograma", TipoCardapio.FIXO),
                                  (3, "Barraquinha de Tapioca", "tapioca", TipoCardapio.FIXO)]:
        ctx.restaurantes.salvar(Restaurante(rid, nome, "Campus Impatech", time(8), time(11), tipo))
        ctx.usuarios.salvar(Usuario(rid, nome, f"{slug}@exemplo.com", senha_hash, "21999999999", PapelUsuario.PARCEIRO, rid))
    ctx.usuarios.salvar(Usuario(4, "Aluno de demonstração", "aluno@impatech.edu.br", senha_hash, "21999999999", PapelUsuario.ALUNO))
