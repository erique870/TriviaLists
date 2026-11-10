"""Gera as URLs de renderização dos .puml em um servidor PlantUML.

Não faz requisição: apenas imprime as URLs, para você abrir no navegador ou
baixar com curl. Útil quando não há Java na máquina.

    python docs/diagramas/gerar_urls.py              # servidor público
    python docs/diagramas/gerar_urls.py --svg
    python docs/diagramas/gerar_urls.py --servidor http://localhost:8080

Atenção: o servidor público recebe o conteúdo do diagrama codificado na URL.
Para manter tudo local, suba o servidor oficial em contêiner e aponte --servidor
para ele:

    docker run -d -p 8080:8080 plantuml/plantuml-server:jetty
"""

from __future__ import annotations

import argparse
import pathlib
import zlib

ALFABETO = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"


def codificar(texto: str) -> str:
    """Compressão deflate seguida do base64 com o alfabeto próprio do PlantUML."""
    bruto = zlib.compress(texto.encode("utf-8"))[2:-4]
    saida: list[str] = []
    for i in range(0, len(bruto), 3):
        bloco = bruto[i : i + 3]
        bloco = bloco + b"\0" * (3 - len(bloco))
        numero = (bloco[0] << 16) | (bloco[1] << 8) | bloco[2]
        saida += [ALFABETO[(numero >> deslocamento) & 0x3F] for deslocamento in (18, 12, 6, 0)]
    return "".join(saida)


def main() -> None:
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument("--servidor", default="https://www.plantuml.com/plantuml")
    analisador.add_argument("--svg", action="store_true", help="gera SVG em vez de PNG")
    analisador.add_argument("--curl", action="store_true", help="imprime comandos curl prontos")
    argumentos = analisador.parse_args()

    formato = "svg" if argumentos.svg else "png"
    pasta = pathlib.Path(__file__).parent
    saida = pasta.parent.parent / "img"

    nomes = {
        "01-casos-de-uso": "Casos_de_uso",
        "02-classes": "Classes",
        "03-sequencia-criar-pedido": "Sequencia_FazerPedido",
        "04-sequencia-criar-lista": "Sequencia_CriarLista",
        "05-sequencia-fechar-lista": "Sequencia_FecharLista",
        "06-atividades": "Atividades",
        "07-componentes": "Componentes",
    }

    for arquivo in sorted(pasta.glob("*.puml")):
        url = f"{argumentos.servidor}/{formato}/{codificar(arquivo.read_text(encoding='utf-8'))}"
        destino = saida / f"{nomes.get(arquivo.stem, arquivo.stem)}.{formato}"
        if argumentos.curl:
            print(f'curl -s -o "{destino}" "{url}"')
        else:
            print(f"{arquivo.stem}\n  {url}\n")


if __name__ == "__main__":
    main()
