/**
 * TRIVIALISTS - Lógica da Página de Autenticação (Login e Cadastro FA01)
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Se o usuário já tiver sessão ativa válida, redireciona direto para sua tela
    let sessaoExistente = null;
    try {
        const usuario = await validarSessao();
        if (usuario) sessaoExistente = { usuario };
    } catch { /* A tela de acesso continua disponível para tentar novamente. */ }
    if (sessaoExistente && sessaoExistente.usuario) {
        if (sessaoExistente.usuario.papel === 'ALUNO') {
            window.location.href = '/aluno';
            return;
        } else if (sessaoExistente.usuario.papel === 'PARCEIRO') {
            window.location.href = '/parceiro';
            return;
        }
    }

    // Gerenciamento de Abas (Entrar / Novo Aluno)
    const tabLogin = document.getElementById('tab-login');
    const tabCadastro = document.getElementById('tab-cadastro');
    const formLogin = document.getElementById('form-login-container');
    const formCadastro = document.getElementById('form-cadastro-container');

    function alternarAba(aba) {
        limparAlertas();
        if (aba === 'login') {
            tabLogin.classList.add('active');
            tabCadastro.classList.remove('active');
            formLogin.style.display = 'block';
            formCadastro.style.display = 'none';
        } else {
            tabCadastro.classList.add('active');
            tabLogin.classList.remove('active');
            formLogin.style.display = 'none';
            formCadastro.style.display = 'block';
        }
    }

    if (tabLogin && tabCadastro) {
        tabLogin.addEventListener('click', () => alternarAba('login'));
        tabCadastro.addEventListener('click', () => alternarAba('cadastro'));
    }

    // Elementos de Alerta
    const alertBox = document.getElementById('auth-alert');

    function exibirAlerta(mensagem, tipo = 'danger') {
        if (!alertBox) return;
        alertBox.className = `alert alert-${tipo} show`;
        alertBox.textContent = mensagem;
    }

    function limparAlertas() {
        if (!alertBox) return;
        alertBox.className = 'alert';
        alertBox.textContent = '';
    }

    // Mensagens vindas da URL (ex: ?msg=sessao_encerrada)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('msg') === 'sessao_encerrada') {
        exibirAlerta('Sua sessão foi encerrada com sucesso.', 'success');
    } else if (urlParams.get('msg') === 'sessao_expirada') {
        exibirAlerta('Sua sessão expirou. Faça login novamente.', 'danger');
    } else if (urlParams.get('msg') === 'login_necessario') {
        exibirAlerta('Por favor, faça login para acessar esta página.', 'danger');
    }

    // --------------------------------------------------------------------------
    // SUBMISSÃO DO LOGIN (CU08 / FE01)
    // --------------------------------------------------------------------------
    const formLoginForm = document.getElementById('form-login');
    const btnEntrar = document.getElementById('btn-entrar');

    if (formLoginForm) {
        formLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            limparAlertas();

            const email = document.getElementById('login-email').value.trim();
            const senha = document.getElementById('login-senha').value;

            if (!email || !senha) {
                exibirAlerta('Informe seu e-mail e sua senha para entrar.');
                return;
            }

            btnEntrar.disabled = true;
            btnEntrar.textContent = 'Entrando...';

            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, senha }),
                });

                const data = await response.json();

                if (response.ok) {
                    salvarSessao(data.access_token, data.usuario);

                    // Redirecionamento por papel (RN05)
                    if (data.usuario.papel === 'ALUNO') {
                        window.location.href = '/aluno';
                    } else if (data.usuario.papel === 'PARCEIRO') {
                        window.location.href = '/parceiro';
                    } else {
                        window.location.href = '/';
                    }
                } else {
                    // FE01: Mensagem de erro segura
                    exibirAlerta(data.detail || 'E-mail ou senha incorretos.');
                }
            } catch (err) {
                exibirAlerta('Não foi possível conectar ao servidor. Verifique sua conexão.');
            } finally {
                btnEntrar.disabled = false;
                btnEntrar.textContent = 'Entrar na Plataforma';
            }
        });
    }

    // --------------------------------------------------------------------------
    // SUBMISSÃO DO CADASTRO DE ALUNO (FA01)
    // --------------------------------------------------------------------------
    const formCadastroForm = document.getElementById('form-cadastro');
    const btnCadastrar = document.getElementById('btn-cadastrar');

    if (formCadastroForm) {
        formCadastroForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            limparAlertas();

            const nome = document.getElementById('cad-nome').value.trim();
            const email = document.getElementById('cad-email').value.trim();
            const telefone = document.getElementById('cad-telefone').value.trim();
            const senha = document.getElementById('cad-senha').value;
            const confirmaSenha = document.getElementById('cad-confirma-senha').value;

            if (senha !== confirmaSenha) {
                exibirAlerta('A confirmação da senha não confere.');
                return;
            }

            if (senha.length < 6) {
                exibirAlerta('A senha deve ter no mínimo 6 caracteres.');
                return;
            }

            btnCadastrar.disabled = true;
            btnCadastrar.textContent = 'Criando sua conta...';

            try {
                const response = await fetch('/auth/cadastro', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome, email, telefone, senha }),
                });

                const data = await response.json();

                if (response.status === 201) {
                    salvarSessao(data.access_token, data.usuario);
                    exibirAlerta('Conta criada com sucesso! Redirecionando...', 'success');
                    setTimeout(() => {
                        window.location.href = '/aluno';
                    }, 600);
                } else if (response.status === 409) {
                    exibirAlerta(data.detail || 'Já existe um aluno cadastrado com este e-mail.');
                } else {
                    exibirAlerta(data.detail || 'Erro ao realizar cadastro. Verifique os dados.');
                }
            } catch (err) {
                exibirAlerta('Erro de conexão ao tentar cadastrar. Tente novamente.');
            } finally {
                btnCadastrar.disabled = false;
                btnCadastrar.textContent = 'Criar Conta de Aluno';
            }
        });
    }
});
