"""Script para testar a conexão e fazer um SELECT no banco Supabase."""

import json
import urllib.request

# Dados do seu projeto Supabase
SUPABASE_URL = "https://kxtmukyspqghzzztpgrd.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4dG11a3lzcHFnaHp6enRwZ3JkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM2NDA5OTUsImV4cCI6MjEwOTIxNjk5NX0."
    "ZiFAuh_NsRKo-hDErTsQEifm_kQQ2wWHBMBEJc9qj8o"
)


def testar_select_restaurantes():
    print("[1/2] Conectando ao Supabase...")
    url = f"{SUPABASE_URL}/rest/v1/restaurantes?select=id,nome,tipo_cardapio,ativo"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        dados = json.loads(response.read().decode("utf-8"))

    print("[2/2] SELECT executado com sucesso!\n")
    print("--- Restaurantes Cadastrados ---")
    for r in dados:
        print(f" • ID: {r['id']} | Nome: {r['nome']} | Tipo: {r['tipo_cardapio']} | Ativo: {r['ativo']}")

    print("\n Conexão com o banco confirmada e funcionando!")


if __name__ == "__main__":
    testar_select_restaurantes()
