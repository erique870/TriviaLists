# Diagramas

Fontes PlantUML dos diagramas do relatório. Antes desta pasta existiam apenas os PNG
em `img/`, sem fonte: alterar um diagrama exigia refazê-lo do zero.

| Fonte | Gera | Caso de uso |
|---|---|---|
| `01-casos-de-uso.puml` | `img/DiagramaCasosDeUso.png` | visão geral |
| `02-classes.puml` | `img/diagrama_classe.png` | domínio |
| `03-sequencia-criar-pedido.puml` | `img/diagrama_seq_criarPedido.png` | CU02 |
| `04-sequencia-criar-lista.puml` | `img/diagrama_seq_criarLista.png` | CU04 |
| `05-sequencia-fechar-lista.puml` | `img/diagrama_seq_fecharLista.png` | CU05 + CU06 |
| `06-atividades.puml` | `img/DiagramaAtividadesNovo.png` | fluxo completo |
| `07-componentes.puml` | `img/diagrama_componente.png` | arquitetura |

Os nomes de saída são os que o `README.md` já referencia, então regerar não exige
mexer no relatório.

## Como gerar

PlantUML precisa de Java. Qualquer um dos caminhos abaixo serve.

**VS Code**: instale a extensão PlantUML (`jebbs.plantuml`), abra o `.puml` e use
`Alt+D` para pré-visualizar ou a paleta de comandos, `PlantUML: Export Current Diagram`.

**Linha de comando**, com o `plantuml.jar` baixado de plantuml.com:

```bash
java -jar plantuml.jar -tpng -o ../../img docs/diagramas/*.puml
```

**IntelliJ**: o plugin PlantUML Integration renderiza no editor.

## Convenções adotadas

Nenhum `skinparam ParticipantPadding`. As versões anteriores usavam essa diretiva,
e o aviso `Please use CSS style instead of skinparam ParticipantPadding` ficou
renderizado dentro dos PNG entregues no relatório.

Apelidos de participante não usam palavras reservadas do PlantUML. `par`, por
exemplo, abre bloco paralelo e não pode ser apelido do ator Parceiro.

Atributos e métodos foram conferidos contra o código, não contra a versão anterior
do diagrama. Onde o diagrama antigo divergia do código, o código prevaleceu, exceto
na terminologia do ator, que segue a padronização em Cliente.
