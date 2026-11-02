"""Arquivo auxiliar pra ler as tabelas do supabase"""

import json
import os
import re
import urllib.request
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def carregar_env() -> dict[str, str]:
    """Carrega variáveis do arquivo .env."""
    env_vars = {}
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
    return env_vars


def buscar_dados_tabela(url_base: str, api_key: str, tabela: str) -> list[dict]:
    """Faz um SELECT * com a API do Supabase."""
    url = f"{url_base}/rest/v1/{tabela}?select=*"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return [{"ERRO": f"Falha ao carregar: {e}"}]


def exibir_tabelas():
    env = carregar_env()
    url_base = env.get("SUPABASE_URL", "https://kxtmukyspqghzzztpgrd.supabase.co")
    api_key = env.get(
        "SUPABASE_ANON_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4dG11a3lzcHFnaHp6enRwZ3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM2NDA5OTUsImV4cCI6MjEwOTIxNjk5NX0.ZiFAuh_NsRKo-hDErTsQEifm_kQQ2wWHBMBEJc9qj8o",
    )

    tabelas_ordem = [
        ("restaurantes", "Restaurantes Parceiros"),
        ("usuarios", "Usuários (Alunos e Parceiros)"),
        ("produtos", "Catálogo de Produtos"),
        ("listas_diarias", "Listas Diárias de Refeições"),
        ("lista_produtos", "Produtos Disponíveis na Lista (Cardápio do Dia)"),
        ("pedidos", "Pedidos Realizados"),
        ("itens_pedido", "Itens dos Pedidos"),
    ]

    console = Console() if HAS_RICH else None

    if console:
        console.print(
            Panel.fit(
                "[bold cyan]TRIVIALISTS[/bold cyan] - [bold green]Visão Geral do Banco no Supabase[/bold green]\n"
                f"[dim]Conectado em: {url_base}[/dim]",
                box=box.ROUNDED,
            )
        )
    else:
        print("=" * 70)
        print(" TRIVIALISTS - Visão Geral do Banco no Supabase ")
        print(f" Conectado em: {url_base}")
        print("=" * 70)

    for nome_tabela, descricao in tabelas_ordem:
        dados = buscar_dados_tabela(url_base, api_key, nome_tabela)
        qtd = len(dados)

        if console:
            tabela_rich = Table(
                title=f"[bold yellow]{nome_tabela}[/bold yellow] ({qtd} registro{'s' if qtd != 1 else ''}) - [dim]{descricao}[/dim]",
                box=box.ROUNDED,
                header_style="bold magenta",
                title_justify="left",
            )

            if not dados:
                tabela_rich.add_column("Status")
                tabela_rich.add_row("[italic dim](nenhum registro encontrado)[/italic dim]")
            else:
                colunas = list(dados[0].keys())
                for col in colunas:
                    tabela_rich.add_column(col, style="cyan" if "id" in col else "white")

                for linha in dados:
                    valores = []
                    for col in colunas:
                        val = linha.get(col)
                        # Mascarar hash de senha para exibição limpa
                        if col == "senha_hash" and val:
                            val = f"{str(val)[:12]}..."
                        # Limpar datas ISO longas
                        elif isinstance(val, str) and "T" in val and len(val) > 19:
                            val = val[:19].replace("T", " ")
                        valores.append(str(val) if val is not None else "[dim]NULL[/dim]")
                    tabela_rich.add_row(*valores)

            console.print(tabela_rich)
            console.print()
        else:
            print(f"\n--- {nome_tabela} ({qtd} registros) - {descricao} ---")
            if not dados:
                print("  (nenhum registro)")
            else:
                for linha in dados:
                    print(f"  {linha}")


if __name__ == "__main__":
    exibir_tabelas()
