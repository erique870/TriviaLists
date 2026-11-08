/** Sessão validada no servidor e chamadas autenticadas compartilhadas. */
const CHAVE_TOKEN = 'trivialists_token';
const CHAVE_USUARIO = 'trivialists_usuario';

function obterSessao() {
    const token = localStorage.getItem(CHAVE_TOKEN);
    try {
        const usuario = JSON.parse(localStorage.getItem(CHAVE_USUARIO));
        return token && usuario ? { token, usuario } : null;
    } catch {
        localStorage.removeItem(CHAVE_TOKEN);
        localStorage.removeItem(CHAVE_USUARIO);
        return null;
    }
}

function salvarSessao(token, usuario) {
    localStorage.setItem(CHAVE_TOKEN, token);
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
}

function encerrarSessao(motivo = 'sessao_encerrada') {
    localStorage.removeItem(CHAVE_TOKEN);
    localStorage.removeItem(CHAVE_USUARIO);
    window.location.href = '/?msg=' + encodeURIComponent(motivo);
}

async function validarSessao() {
    const sessao = obterSessao();
    if (!sessao) return null;
    const resposta = await fetch('/auth/me', { headers: { Authorization: `Bearer ${sessao.token}` } });
    if (resposta.status === 401) {
        localStorage.removeItem(CHAVE_TOKEN);
        localStorage.removeItem(CHAVE_USUARIO);
        return null;
    }
    if (!resposta.ok) throw new Error('Não foi possível validar sua sessão. Tente novamente.');
    const usuario = await resposta.json();
    salvarSessao(sessao.token, usuario);
    return usuario;
}

async function protegerRota(papelEsperado) {
    const usuario = await validarSessao();
    if (!usuario) {
        encerrarSessao('login_necessario');
        return null;
    }
    if (usuario.papel !== papelEsperado) {
        window.location.href = usuario.papel === 'ALUNO' ? '/aluno' : '/parceiro';
        return null;
    }
    for (const [id, texto] of [['user-nome', usuario.nome], ['user-email', usuario.email],
        ['user-papel', usuario.papel], ['user-avatar', usuario.nome.charAt(0).toUpperCase()]]) {
        const elemento = document.getElementById(id);
        if (elemento) elemento.textContent = texto;
    }
    return usuario;
}

async function api(caminho, opcoes = {}) {
    const sessao = obterSessao();
    if (!sessao) {
        encerrarSessao('login_necessario');
        throw new Error('Faça login novamente.');
    }
    const resposta = await fetch(caminho, { ...opcoes, headers: {
        'Content-Type': 'application/json', Authorization: `Bearer ${sessao.token}`, ...opcoes.headers,
    }});
    if (resposta.status === 401) {
        encerrarSessao('sessao_expirada');
        throw new Error('Sessão expirada.');
    }
    const dados = await resposta.json();
    if (!resposta.ok) {
        const mensagem = Array.isArray(dados.detail)
            ? dados.detail.map(erro => erro.msg).join('; ') : dados.detail;
        throw new Error(mensagem || 'Não foi possível concluir a operação.');
    }
    return dados;
}

function escapar(valor) {
    return String(valor ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
const moeda = valor => Number(valor).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const horario = valor => new Date(valor).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
function avisar(mensagem, sucesso = false) {
    const alerta = document.getElementById('app-alert');
    if (!alerta) return;
    alerta.className = `alert show alert-${sucesso ? 'success' : 'danger'}`;
    alerta.textContent = mensagem;
}

async function executarBotao(botao, operacao) {
    botao.disabled = true;
    try { await operacao(); } catch (erro) { avisar(erro.message); }
    finally { botao.disabled = false; }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-logout')?.addEventListener('click', () => encerrarSessao());
});
