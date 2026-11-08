/** CU01, CU02 e CU03, com consultas e confirmações reais da API. */
document.addEventListener('DOMContentLoaded', async () => {
    const listasEl = document.getElementById('listas');
    const pedidosEl = document.getElementById('pedidos');
    const avisosEl = document.getElementById('notificacoes');
    const filtro = document.getElementById('filtro-restaurante');
    let carregando = false;

    async function atualizar() {
        if (carregando) return;
        carregando = true;
        const rascunhos = new Map([...listasEl.querySelectorAll('input[data-produto]')]
            .map(input => [`${input.closest('form').dataset.lista}-${input.dataset.produto}`, input.value]));
        try {
            const [resposta, pedidos, avisos] = await Promise.all([
                api('/api/listas' + (filtro.value ? '?restaurante_id=' + encodeURIComponent(filtro.value) : '')),
                api('/api/pedidos'), api('/api/notificacoes'),
            ]);
            listasEl.innerHTML = resposta.listas.length ? resposta.listas.map(lista => {
                const ativo = pedidos.find(p => p.lista_diaria_id === lista.id && p.status === 'ATIVO');
                return `<form class="entry" data-lista="${lista.id}">
                    <h3>${escapar(lista.restaurante)}</h3><p>Pedidos até ${horario(lista.horario_fechamento)}</p>
                    ${lista.produtos.filter(p => p.disponivel).map(p => `<label class="menu-item"><span>${escapar(p.nome)} · ${moeda(p.preco)}<small>${escapar(p.descricao)}</small></span>
                        <input class="form-control" type="number" min="0" max="1000" step="1" value="${escapar(rascunhos.get(`${lista.id}-${p.id}`) || '0')}" data-produto="${p.id}" data-preco="${p.preco}" aria-label="Quantidade de ${escapar(p.nome)}" ${ativo ? 'disabled' : ''}></label>`).join('')}
                    <div class="order-total">Total: <span data-total>${moeda(0)}</span></div>
                    ${ativo ? `<p>${ativo.concluido ? `O pedido #${ativo.id} já foi concluído e retirado.` : `Você já tem o pedido #${ativo.id} nesta lista. Para refazer, cancele-o em Meus pedidos dentro do prazo.`}</p>` : '<button class="btn btn-primary" type="submit">Confirmar pedido</button>'}
                </form>`;
            }).join('') : `<p class="entry">${escapar(resposta.mensagem)}</p>`;
            listasEl.querySelectorAll('form').forEach(calcularTotal);
            pedidosEl.innerHTML = pedidos.length ? pedidos.map(p => `<article class="entry">
                <div class="section-heading"><h3>Pedido #${p.id} · ${escapar(p.restaurante)}</h3><span class="badge">${p.concluido ? 'CONCLUÍDO' : escapar(p.status)}</span></div>
                <p>${p.itens.map(i => `${i.quantidade} × ${escapar(i.produto)} (${moeda(i.preco_unitario)})`).join('<br>')}</p>
                <p>Total: <strong>${moeda(p.valor_total)}</strong> · Retirada: ${escapar(p.status_retirada)}</p>
                ${p.pode_cancelar ? `<button type="button" class="btn btn-danger-outline" data-cancelar="${p.id}">Cancelar pedido</button>` : ''}
            </article>`).join('') : '<p class="entry">Você ainda não fez pedidos.</p>';
            const naoLidos = avisos.filter(n => !n.lida);
            avisosEl.innerHTML = naoLidos.length ? naoLidos.slice(0, 10).map(n => `<div class="entry"><p>${escapar(n.mensagem)}</p><button class="btn btn-outline" data-ler="${n.id}">Marcar como lido</button></div>`).join('') : '<p>Nenhum aviso novo.</p>';
        } catch (erro) { avisar(erro.message); }
        finally { carregando = false; }
    }

    function calcularTotal(form) {
        const total = [...form.querySelectorAll('input[data-produto]')].reduce((soma, i) => soma + Number(i.value) * Number(i.dataset.preco), 0);
        form.querySelector('[data-total]').textContent = moeda(total);
    }
    listasEl.addEventListener('input', e => {
        if (e.target.matches('input[data-produto]')) calcularTotal(e.target.closest('form'));
    });
    listasEl.addEventListener('submit', e => {
        e.preventDefault();
        const form = e.target;
        const itens = [...form.querySelectorAll('input[data-produto]')].filter(i => Number(i.value) > 0)
            .map(i => ({ produto_id: Number(i.dataset.produto), quantidade: Number(i.value) }));
        if (!itens.length) { avisar('Escolha ao menos um produto.'); return; }
        executarBotao(form.querySelector('button'), async () => {
            const pedido = await api('/api/pedidos', { method: 'POST', body: JSON.stringify({ lista_id: Number(form.dataset.lista), itens }) });
            avisar(`Pedido #${pedido.id} confirmado! Total: ${moeda(pedido.valor_total)}.`, true);
            await atualizar();
        });
    });
    pedidosEl.addEventListener('click', e => {
        const botao = e.target.closest('[data-cancelar]');
        if (!botao) return;
        executarBotao(botao, async () => {
            await api(`/api/pedidos/${botao.dataset.cancelar}/cancelar`, { method: 'POST' });
            avisar('Pedido cancelado com sucesso.', true);
            await atualizar();
        });
    });
    avisosEl.addEventListener('click', e => {
        const botao = e.target.closest('[data-ler]');
        if (botao) executarBotao(botao, async () => {
            await api(`/api/notificacoes/${botao.dataset.ler}/ler`, { method: 'POST' });
            await atualizar();
        });
    });
    document.getElementById('atualizar').addEventListener('click', atualizar);
    filtro.addEventListener('change', atualizar);
    try {
        if (!await protegerRota('ALUNO')) return;
        const restaurantes = await api('/api/restaurantes');
        filtro.innerHTML += restaurantes.map(r => `<option value="${r.id}">${escapar(r.nome)}</option>`).join('');
        await atualizar();
        setInterval(() => { if (!document.hidden) atualizar(); }, 30000);
    } catch (erro) { avisar(erro.message); }
});
