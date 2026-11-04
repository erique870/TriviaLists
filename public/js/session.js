/**
 * TRIVIALISTS - Gerenciamento de Sessão e Guarda de Rotas no Cliente
 */

const CHAVE_TOKEN = 'trivialists_token';
const CHAVE_USUARIO = 'trivialists_usuario';

function obterSessao() {
    const token = localStorage.getItem(CHAVE_TOKEN);
    const usuarioRaw = localStorage.getItem(CHAVE_USUARIO);
    if (!token || !usuarioRaw) {
        return null;
    }
    try {
        const usuario = JSON.parse(usuarioRaw);
        return { token, usuario };
    } catch {
        encerrarSessao();
        return null;
    }
}

function salvarSessao(token, usuario) {
    localStorage.setItem(CHAVE_TOKEN, token);
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
}

function encerrarSessao() {
    localStorage.removeItem(CHAVE_TOKEN);
    localStorage.removeItem(CHAVE_USUARIO);
    window.location.href = '/?msg=sessao_encerrada';
}

function protegerRota(papelEsperado) {
    const sessao = obterSessao();
    if (!sessao) {
        window.location.href = '/?msg=login_necessario';
        return;
    }

    const { usuario } = sessao;

    // RN05: Garante que alunos não acessem visão do parceiro e vice-versa
    if (papelEsperado && usuario.papel !== papelEsperado) {
        if (usuario.papel === 'ALUNO') {
            window.location.href = '/aluno';
        } else if (usuario.papel === 'PARCEIRO') {
            window.location.href = '/parceiro';
        }
        return;
    }

    // Preenche informações visuais do usuário na página se existirem os elementos
    const elNome = document.getElementById('user-nome');
    const elEmail = document.getElementById('user-email');
    const elPapel = document.getElementById('user-papel');
    const elAvatar = document.getElementById('user-avatar');

    if (elNome) elNome.textContent = usuario.nome;
    if (elEmail) elEmail.textContent = usuario.email;
    if (elPapel) elPapel.textContent = usuario.papel;
    if (elAvatar && usuario.nome) {
        elAvatar.textContent = usuario.nome.charAt(0).toUpperCase();
    }
}

// Configura botão de logout se existir na página
document.addEventListener('DOMContentLoaded', () => {
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
        btnLogout.addEventListener('click', (e) => {
            e.preventDefault();
            encerrarSessao();
        });
    }
});
