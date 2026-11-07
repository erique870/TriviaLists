-- ==============================================================================
-- TRIVIALISTS - Dados Iniciais de Teste e Homologação (Seed)
-- ==============================================================================

-- No momento, os dados são só vários exemplos. Todos inseridos só pra teste.

-- 1. Inserir parceiros comerciais iniciais do Impatech
INSERT INTO restaurantes (id, nome, endereco, horario_padrao_abertura, horario_padrao_fechamento, tipo_cardapio, ativo)
VALUES
    (1, 'Salsalito', 'Prédio Principal, Térreo', '06:00:00', '10:00:00', 'VARIAVEL', TRUE),
    (2, 'Pilograma', 'Área de Convivência', '08:00:00', '11:30:00', 'FIXO', TRUE),
    (3, 'Barraquinha de Tapioca', 'Pátio Externo', '07:30:00', '10:30:00', 'FIXO', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Atualizar sequence dos restaurantes
SELECT setval('restaurantes_id_seq', (SELECT MAX(id) FROM restaurantes));

-- Como Inserir Usuários (1 Cliente e 1 Parceiro Salsalito)
-- Senha padrão para testes de login: 'senha123'
INSERT INTO usuarios (id, nome, email, senha_hash, telefone, papel, restaurante_id)
VALUES
    (1, 'Erique Silva', 'erique.teste@impatech.edu.br', 'scrypt$a1b2c3d4e5f60718$1b63f962d6f275a47d98a7bf67cd379b57089c627a8317fc7457424648987731f2331b5f1be80be5e620b8f436978b7a716bc2b54ba2932d95d0952d9e96202f', '21999990001', 'CLIENTE', NULL),
    (2, 'Gerente Salsalito', 'teste@salsalito.com.br', 'scrypt$a1b2c3d4e5f60718$1b63f962d6f275a47d98a7bf67cd379b57089c627a8317fc7457424648987731f2331b5f1be80be5e620b8f436978b7a716bc2b54ba2932d95d0952d9e96202f', '21999990002', 'PARCEIRO', 1)
ON CONFLICT (id) DO UPDATE SET
    nome = EXCLUDED.nome,
    email = EXCLUDED.email,
    senha_hash = EXCLUDED.senha_hash,
    telefone = EXCLUDED.telefone,
    papel = EXCLUDED.papel,
    restaurante_id = EXCLUDED.restaurante_id;

SELECT setval('usuarios_id_seq', (SELECT MAX(id) FROM usuarios));

-- 3. Inserir Produtos no catálogo permanente
INSERT INTO produtos (id, restaurante_id, nome, descricao, preco, disponivel)
VALUES
    -- Salsalito (Restaurante 1)
    (1, 1, 'Quentinha do Dia (Frango Grelhado + Salada)', 'Arroz, feijão, filé de frango grelhado e salada da casa', 22.00, TRUE),
    (2, 1, 'Quentinha do Dia (Carne Assada)', 'Arroz, feijão tropeiro e carne bovina assada ao molho madeira', 25.00, TRUE),
    (3, 1, 'Suco de Laranja Natural 300ml', 'Sem adição de açúcar', 6.00, TRUE),
    
    -- Pilograma (Restaurante 2 - Fixo)
    (4, 2, 'PF Executivo de Frango à Milanesa', 'Acompanha arroz, feijão e batata frita', 20.00, TRUE),
    (5, 2, 'PF Executivo Bife Acebolado', 'Acompanha arroz, feijão e purê', 23.00, TRUE),
    (6, 2, 'Refrigerante Lata 350ml', 'Coca-Cola ou Guaraná', 5.00, TRUE),

    -- Barraquinha de Tapioca (Restaurante 3 - Fixo)
    (7, 3, 'Tapioca Frango c/ Catupiry', 'Frango desfiado com requeijão cremoso', 14.00, TRUE),
    (8, 3, 'Tapioca Queijo Coalho e Banana', 'Queijo coalho chapeado com banana e canela', 12.00, TRUE)
ON CONFLICT (id) DO NOTHING;

SELECT setval('produtos_id_seq', (SELECT MAX(id) FROM produtos));

-- 4. Criar uma Lista Diária ABERTA para hoje (Salsalito)
-- Aberta desde as 08:00 até as 23:59 de hoje para permitir testes a qualquer momento
INSERT INTO listas_diarias (id, restaurante_id, data, horario_abertura, horario_fechamento, status)
VALUES
    (1, 1, CURRENT_DATE, CURRENT_DATE + TIME '08:00:00', CURRENT_DATE + TIME '23:59:59', 'ABERTA')
ON CONFLICT (id) DO NOTHING;

SELECT setval('listas_diarias_id_seq', (SELECT MAX(id) FROM listas_diarias));

-- 5. Vincular produtos à lista do dia (Salsalito oferece os produtos 1, 2 e 3 hoje)
INSERT INTO lista_produtos (lista_diaria_id, produto_id)
VALUES
    (1, 1),
    (1, 2),
    (1, 3)
ON CONFLICT DO NOTHING;
