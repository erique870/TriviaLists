/** CU04 a CU07: catálogo, publicação, abertura, fechamento e produção. */
document.addEventListener('DOMContentLoaded', async () => {
    let produtos = [];
    let carregando = false;
    let listaRetiradas = null;
    const produtoForm = document.getElementById('form-produto');
    const listaForm = document.getElementById('form-lista');
    const hoje = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
    document.getElementById('lista-data').value = hoje;

    async function atualizar() {
        if (carregando) return;
        carregando = true;
        try {
            const [catalogo, listas] = await Promise.all([api('/api/parceiro/produtos'), api('/api/parceiro/listas')]);
            produtos = catalogo;
            const selecionados = new Set([...document.querySelectorAll('#lista-produtos input:checked')].map(i => i.value));
            document.getElementById('produtos').innerHTML = produtos.length ? produtos.map(p => `<div class="entry">
                <div class="section-heading"><h3>${escapar(p.nome)} · ${moeda(p.preco)}</h3><span class="badge">${p.disponivel ? 'Disponível' : 'Indisponível'}</span></div>
                <p>${escapar(p.descricao)}</p><div class="actions"><button class="btn btn-outline" data-editar="${p.id}">Editar</button>
                <button class="btn btn-outline" data-disponibilidade="${p.id}">${p.disponivel ? 'Desativar' : 'Disponibilizar'}</button>
                <button class="btn btn-danger-outline" data-excluir="${p.id}">Excluir</button></div></div>`).join('') : '<p class="entry">Cadastre o primeiro produto para publicar um cardápio.</p>';
            document.getElementById('lista-produtos').innerHTML = produtos.filter(p => p.disponivel).map(p => `<label class="check-label"><input type="checkbox" value="${p.id}" ${selecionados.has(String(p.id)) ? 'checked' : ''}> ${escapar(p.nome)} · ${moeda(p.preco)}</label>`).join('') || '<p>Nenhum produto disponível.</p>';
            document.getElementById('listas').innerHTML = listas.length ? listas.map(l => `<article class="entry"><h3>Lista #${l.id} · ${escapar(l.data.split('-').reverse().join('/'))}</h3>
                <p>${horario(l.horario_abertura)} até ${horario(l.horario_fechamento)} · <span class="badge">${escapar(l.status)}</span></p>
                <p>${l.produtos.map(p => escapar(p.nome)).join(', ')}</p><div class="actions">
                ${l.status === 'ABERTA' ? `<button class="btn btn-outline" data-acao="fechar" data-lista="${l.id}">Fechar e gerar relatório</button>` : `<button class="btn btn-outline" data-acao="relatorio" data-lista="${l.id}">Ver relatório</button>${new Date(l.horario_fechamento) > new Date() ? `<button class="btn btn-outline" data-acao="abrir" data-lista="${l.id}">Reabrir lista</button>` : ''}`}
                <button class="btn btn-outline" data-acao="pedidos" data-lista="${l.id}">Pedidos e retiradas</button>
                </div></article>`).join('') : '<p class="entry">Nenhuma lista publicada.</p>';
            if (listaRetiradas !== null) await atualizarRetiradas();
        } catch (erro) { avisar(erro.message); }
        finally { carregando = false; }
    }

    function mostrarRelatorio(r) {
        document.getElementById('painel-relatorio').hidden = false;
        document.getElementById('relatorio').innerHTML = `<h3>Lista #${r.lista_id} · ${escapar(r.data.split('-').reverse().join('/'))}</h3>
            ${r.mensagem ? `<p>${escapar(r.mensagem)}</p>` : `<div class="table-scroll"><table><thead><tr><th>Produto</th><th>Quantidade</th></tr></thead><tbody>${r.itens.map(i => `<tr><td>${escapar(i.produto)}</td><td>${i.quantidade}</td></tr>`).join('')}</tbody></table></div>`}
            <p>${r.total_pedidos} pedido(s) ativo(s)</p><p class="order-total">Valor total: ${moeda(r.valor_total)}</p>`;
    }

    async function atualizarRetiradas() {
        if (listaRetiradas === null) return;
        const lista = listaRetiradas;
        const pedidos = await api(`/api/parceiro/listas/${lista}/pedidos`);
        if (lista !== listaRetiradas) return;
        document.getElementById('painel-retiradas').hidden = false;
        document.getElementById('titulo-retiradas').textContent = `Pedidos e retiradas · Lista #${lista}`;
        const pendentes = pedidos.filter(p => p.status === 'ATIVO' && !p.concluido).length;
        const retirados = pedidos.filter(p => p.concluido).length;
        document.getElementById('pedidos-retirada').innerHTML = pedidos.length
            ? `<p>${pendentes} retirada(s) pendente(s) · ${retirados} pedido(s) concluído(s)</p>` + pedidos.map(p => `<article class="entry" data-pedido="${p.id}">
                <div class="section-heading"><h3>Pedido #${p.id} · ${escapar(p.cliente)}</h3><span class="badge">${p.concluido ? 'CONCLUÍDO' : escapar(p.status)}</span></div>
                <p>${p.itens.map(i => `${i.quantidade} × ${escapar(i.produto)} (${moeda(i.preco_unitario)})`).join('<br>')}</p>
                <p>Total: <strong>${moeda(p.valor_total)}</strong>${p.status === 'ATIVO' ? ` · Retirada: ${escapar(p.status_retirada)}` : ''}</p>
                ${p.status === 'ATIVO' && !p.concluido ? `<button class="btn btn-outline" data-confirmar-retirada="${p.id}" data-lista="${lista}">Confirmar retirada</button>` : ''}
                </article>`).join('')
            : '<p class="entry">Nenhum pedido registrado nesta lista.</p>';
    }

    document.getElementById('pedidos-retirada').addEventListener('click', e => {
        const botao = e.target.closest('[data-confirmar-retirada]');
        if (!botao) return;
        executarBotao(botao, async () => {
            const pedido = await api(`/api/parceiro/listas/${botao.dataset.lista}/pedidos/${botao.dataset.confirmarRetirada}/retirada`, { method: 'POST' });
            avisar(`Pedido #${pedido.id} concluído: retirada confirmada.`, true);
            await atualizarRetiradas();
        });
    });
    document.getElementById('atualizar-retiradas').addEventListener('click', e => {
        executarBotao(e.target, atualizarRetiradas);
    });

    document.getElementById('produtos').addEventListener('click', e => {
        const excluir = e.target.closest('[data-excluir]');
        if (excluir) {
            const p = produtos.find(p => p.id === Number(excluir.dataset.excluir));
            if (!p || !window.confirm(`Excluir definitivamente o produto "${p.nome}"? Esta ação não pode ser desfeita.`)) return;
            executarBotao(excluir, async () => {
                const resposta = await api(`/api/parceiro/produtos/${p.id}`, { method: 'DELETE' });
                if (document.getElementById('produto-id').value === String(p.id)) {
                    produtoForm.reset();
                    document.getElementById('produto-id').value = '';
                }
                avisar(resposta.mensagem, true);
                await atualizar();
            });
            return;
        }
        const editar = e.target.closest('[data-editar]');
        if (editar) {
            const p = produtos.find(p => p.id === Number(editar.dataset.editar));
            for (const [campo, valor] of [['id', p.id], ['nome', p.nome], ['preco', p.preco], ['descricao', p.descricao]]) {
                document.getElementById('produto-' + campo).value = valor;
            }
            document.getElementById('produto-disponivel').checked = p.disponivel;
            document.getElementById('produto-nome').focus();
        }
        const disponibilidade = e.target.closest('[data-disponibilidade]');
        if (disponibilidade) executarBotao(disponibilidade, async () => {
            const p = produtos.find(p => p.id === Number(disponibilidade.dataset.disponibilidade));
            await api(`/api/parceiro/produtos/${p.id}`, { method: 'PATCH', body: JSON.stringify({ disponivel: !p.disponivel }) });
            avisar('Disponibilidade atualizada.', true);
            await atualizar();
        });
    });
    document.getElementById('limpar-produto').addEventListener('click', () => { produtoForm.reset(); document.getElementById('produto-id').value = ''; });
    produtoForm.addEventListener('submit', e => {
        e.preventDefault();
        executarBotao(produtoForm.querySelector('[type=submit]'), async () => {
            const id = document.getElementById('produto-id').value;
            const dados = { nome: document.getElementById('produto-nome').value, descricao: document.getElementById('produto-descricao').value,
                preco: document.getElementById('produto-preco').value, disponivel: document.getElementById('produto-disponivel').checked };
            await api('/api/parceiro/produtos' + (id ? '/' + id : ''), { method: id ? 'PATCH' : 'POST', body: JSON.stringify(dados) });
            produtoForm.reset(); document.getElementById('produto-id').value = '';
            avisar('Produto salvo com sucesso.', true);
            await atualizar();
        });
    });
    document.getElementById('form-horarios').addEventListener('submit', e => {
        e.preventDefault();
        executarBotao(e.target.querySelector('button'), async () => {
            const dados = { horario_abertura: document.getElementById('padrao-abertura').value, horario_fechamento: document.getElementById('padrao-fechamento').value };
            const resposta = await api('/api/parceiro/restaurante/horarios', { method: 'PATCH', body: JSON.stringify(dados) });
            document.getElementById('lista-abertura').value = dados.horario_abertura;
            document.getElementById('lista-fechamento').value = dados.horario_fechamento;
            avisar(resposta.mensagem, true);
        });
    });
    listaForm.addEventListener('submit', e => {
        e.preventDefault();
        executarBotao(listaForm.querySelector('button'), async () => {
            const dados = { data: document.getElementById('lista-data').value, horario_abertura: document.getElementById('lista-abertura').value,
                horario_fechamento: document.getElementById('lista-fechamento').value,
                produto_ids: [...document.querySelectorAll('#lista-produtos input:checked')].map(i => Number(i.value)) };
            if (!dados.produto_ids.length) throw new Error('Selecione ao menos um produto.');
            const lista = await api('/api/parceiro/listas', { method: 'POST', body: JSON.stringify(dados) });
            avisar(`Cardápio #${lista.id} publicado! Horário limite: ${horario(lista.horario_fechamento)}.`, true);
            await atualizar();
        });
    });
    document.getElementById('listas').addEventListener('click', e => {
        const botao = e.target.closest('[data-acao]');
        if (!botao) return;
        executarBotao(botao, async () => {
            const { acao, lista } = botao.dataset;
            if (acao === 'pedidos') {
                listaRetiradas = Number(lista);
                await atualizarRetiradas();
                document.getElementById('painel-retiradas').scrollIntoView({ behavior: 'smooth', block: 'start' });
                return;
            }
            const dados = await api(`/api/parceiro/listas/${lista}/${acao}`, acao === 'relatorio' ? {} : { method: 'POST' });
            if (acao === 'relatorio') mostrarRelatorio(dados);
            else {
                if (dados.relatorio) mostrarRelatorio(dados.relatorio);
                avisar(acao === 'fechar' ? 'Lista fechada e produção consolidada.' : 'Lista reaberta.', true);
                await atualizar();
            }
        });
    });
    document.getElementById('imprimir').addEventListener('click', () => window.print());
    document.getElementById('atualizar').addEventListener('click', atualizar);
    try {
        if (!await protegerRota('PARCEIRO')) return;
        const r = await api('/api/parceiro/restaurante');
        document.getElementById('padrao-abertura').value = document.getElementById('lista-abertura').value = r.horario_abertura.slice(0, 5);
        document.getElementById('padrao-fechamento').value = document.getElementById('lista-fechamento').value = r.horario_fechamento.slice(0, 5);
        await atualizar();
        setInterval(() => { if (!document.hidden) atualizar(); }, 30000);
    } catch (erro) { avisar(erro.message); }
});
