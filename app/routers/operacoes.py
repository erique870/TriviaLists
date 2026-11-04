"""Adaptadores HTTP dos CU01 a CU07. Identidades vêm da sessão (RN05)."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from app.application.cliente_service import ServicoCliente
from app.application.notificacao_service import ServicoNotificacao
from app.application.restaurante_service import ServicoRestaurante
from app.core.clock import agora
from app.domain import StatusLista, StatusPedido, StatusRetirada, Usuario
from app.routers.deps import require_aluno, require_parceiro
from app.schemas.operacoes import HorariosRequest, ListaRequest, PedidoRequest, ProdutoRequest, ProdutoUpdate

router = APIRouter(prefix="/api", tags=["Listas, pedidos e cardápios"])
Aluno = Annotated[Usuario, Depends(require_aluno)]
Parceiro = Annotated[Usuario, Depends(require_parceiro)]


def contexto(request: Request):
    return request.app.state.contexto


def cliente(ctx=Depends(contexto)):
    return ServicoCliente(ctx)


def parceiro(ctx=Depends(contexto)):
    return ServicoRestaurante(ctx.usuarios, ctx.restaurantes, ctx.produtos, ctx.listas, ctx.transacao,
                             ctx.notificacoes, pedidos=ctx.pedidos)


def lista_publica(lista, ctx):
    restaurante = ctx.restaurantes.obter_por_id(lista.restaurante_id)
    return {"id": lista.id, "restaurante_id": lista.restaurante_id, "restaurante": restaurante.nome,
            "data": lista.data, "horario_abertura": lista.horario_abertura,
            "horario_fechamento": lista.horario_fechamento, "status": lista.status,
            "produtos": [asdict(p) for p in lista.produtos.values()]}


def pedido_publico(pedido, ctx):
    lista = ctx.listas.obter_por_id(pedido.lista_diaria_id)
    restaurante = ctx.restaurantes.obter_por_id(lista.restaurante_id)
    dados = asdict(pedido)
    dados.update(restaurante=restaurante.nome, data=lista.data, horario_fechamento=lista.horario_fechamento,
                 concluido=pedido.status == StatusPedido.ATIVO and pedido.status_retirada == StatusRetirada.RETIRADO,
                 pode_cancelar=pedido.status == StatusPedido.ATIVO and pedido.status_retirada == StatusRetirada.PENDENTE
                 and lista.status == StatusLista.ABERTA and lista.horario_abertura <= agora() < lista.horario_fechamento)
    for item in dados["itens"]:
        item["produto"] = lista.produtos[item["produto_id"]].nome
    return dados


@router.get("/restaurantes")
def restaurantes(usuario: Aluno, ctx=Depends(contexto)):
    return [{"id": r.id, "nome": r.nome, "tipo_cardapio": r.tipo_cardapio} for r in ctx.restaurantes.listar_ativos()]


@router.get("/listas")
def listas_abertas(usuario: Aluno, restaurante_id: int | None = Query(default=None, gt=0),
                   servico=Depends(cliente), ctx=Depends(contexto)):
    listas = servico.listar_abertas(usuario.id, restaurante_id)
    return {"listas": [lista_publica(l, ctx) for l in listas],
            "mensagem": None if listas else "Nenhum restaurante está recebendo pedidos no momento"}


@router.post("/pedidos", status_code=201)
def criar_pedido(dados: PedidoRequest, usuario: Aluno, servico=Depends(cliente), ctx=Depends(contexto)):
    pedido = servico.criar_pedido(usuario.id, dados.lista_id, {i.produto_id: i.quantidade for i in dados.itens})
    return pedido_publico(pedido, ctx)


@router.get("/pedidos")
def meus_pedidos(usuario: Aluno, servico=Depends(cliente), ctx=Depends(contexto)):
    return [pedido_publico(p, ctx) for p in servico.meus_pedidos(usuario.id)]


@router.get("/pedidos/{pedido_id}")
def consultar_pedido(pedido_id: int, usuario: Aluno, ctx=Depends(contexto)):
    pedido = ctx.pedidos.obter_por_id(pedido_id)
    if pedido is None or pedido.usuario_id != usuario.id:
        raise HTTPException(404, "Pedido não encontrado.")
    return pedido_publico(pedido, ctx)


@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, usuario: Aluno, servico=Depends(cliente), ctx=Depends(contexto)):
    return pedido_publico(servico.cancelar_pedido(usuario.id, pedido_id), ctx)


@router.get("/parceiro/restaurante")
def meu_restaurante(usuario: Parceiro, servico=Depends(parceiro)):
    r = servico.obter_restaurante(usuario.id)
    return {"id": r.id, "nome": r.nome, "tipo_cardapio": r.tipo_cardapio,
            "horario_abertura": r.horario_padrao_abertura, "horario_fechamento": r.horario_padrao_fechamento}


@router.patch("/parceiro/restaurante/horarios")
def configurar_horarios(dados: HorariosRequest, usuario: Parceiro, servico=Depends(parceiro)):
    servico.configurar_horarios(usuario.id, dados.horario_abertura, dados.horario_fechamento)
    return {"mensagem": "Horários padrão atualizados para as próximas listas."}


@router.get("/parceiro/produtos")
def produtos(usuario: Parceiro, servico=Depends(parceiro)):
    return [asdict(p) for p in servico.listar_produtos(usuario.id)]


@router.post("/parceiro/produtos", status_code=201)
def cadastrar_produto(dados: ProdutoRequest, usuario: Parceiro, servico=Depends(parceiro)):
    return asdict(servico.cadastrar_produto(usuario.id, **dados.model_dump()))


@router.patch("/parceiro/produtos/{produto_id}")
def atualizar_produto(produto_id: int, dados: ProdutoUpdate, usuario: Parceiro, servico=Depends(parceiro)):
    return asdict(servico.atualizar_produto(usuario.id, produto_id, **dados.model_dump(exclude_unset=True)))


@router.delete("/parceiro/produtos/{produto_id}")
def excluir_produto(produto_id: int, usuario: Parceiro, servico=Depends(parceiro)):
    servico.excluir_produto(usuario.id, produto_id)
    return {"mensagem": "Produto excluído com sucesso."}


@router.get("/parceiro/listas")
def minhas_listas(usuario: Parceiro, servico=Depends(parceiro), ctx=Depends(contexto)):
    return [lista_publica(l, ctx) for l in servico.listar_listas(usuario.id)]


@router.post("/parceiro/listas", status_code=201)
def publicar_lista(dados: ListaRequest, tarefas: BackgroundTasks, usuario: Parceiro,
                   servico=Depends(parceiro), ctx=Depends(contexto)):
    lista = servico.criar_lista_diaria(usuario.id, dados.data, dados.produto_ids, agora(),
                                     dados.horario_abertura, dados.horario_fechamento)
    tarefas.add_task(ServicoNotificacao(ctx).processar)
    return lista_publica(lista, ctx)


@router.post("/parceiro/listas/{lista_id}/abrir")
def abrir_lista(lista_id: int, usuario: Parceiro, servico=Depends(parceiro), ctx=Depends(contexto)):
    return lista_publica(servico.abrir_lista(usuario.id, lista_id, agora()), ctx)


@router.post("/parceiro/listas/{lista_id}/fechar")
def fechar_lista(lista_id: int, usuario: Parceiro, servico=Depends(parceiro), ctx=Depends(contexto)):
    lista = servico.fechar_lista(usuario.id, lista_id)
    return {"lista": lista_publica(lista, ctx), "relatorio": servico.obter_relatorio(usuario.id, lista.id)}


@router.get("/parceiro/listas/{lista_id}/relatorio")
def relatorio(lista_id: int, usuario: Parceiro, servico=Depends(parceiro)):
    return servico.obter_relatorio(usuario.id, lista_id)


@router.get("/parceiro/listas/{lista_id}/pedidos")
def pedidos_da_lista(lista_id: int, usuario: Parceiro, servico=Depends(parceiro), ctx=Depends(contexto)):
    resultado = []
    for pedido in servico.listar_pedidos(usuario.id, lista_id):
        dados = pedido_publico(pedido, ctx)
        aluno = ctx.usuarios.obter_por_id(pedido.usuario_id)
        dados["aluno"] = aluno.nome if aluno is not None else "Aluno não encontrado"
        resultado.append(dados)
    return resultado


@router.post("/parceiro/listas/{lista_id}/pedidos/{pedido_id}/retirada")
def confirmar_retirada(lista_id: int, pedido_id: int, usuario: Parceiro,
                      servico=Depends(parceiro), ctx=Depends(contexto)):
    return pedido_publico(servico.confirmar_retirada(usuario.id, lista_id, pedido_id), ctx)


@router.get("/notificacoes")
def notificacoes(usuario: Aluno, ctx=Depends(contexto)):
    return ctx.notificacoes.listar(usuario.id)


@router.post("/notificacoes/{notificacao_id}/ler")
def ler_notificacao(notificacao_id: int, usuario: Aluno, ctx=Depends(contexto)):
    if not ctx.notificacoes.marcar_lida(usuario.id, notificacao_id):
        raise HTTPException(404, "Notificação não encontrada.")
    return {"mensagem": "Notificação marcada como lida."}
