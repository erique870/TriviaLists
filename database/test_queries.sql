-- ==============================================================================
-- TRIVIALISTS - Bateria de Testes de Validação do Banco no Supabase
-- Execute cada bloco individualmente no SQL Editor para testar as regras
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- TESTE 1 (CU01): Buscar Listas Abertas e seus Cardápios do Dia
-- Deve retornar a lista aberta do Salsalito com os produtos disponíveis
-- ------------------------------------------------------------------------------
SELECT 
    l.id AS lista_id,
    l.data,
    l.status,
    l.horario_abertura,
    l.horario_fechamento,
    r.nome AS restaurante,
    r.tipo_cardapio,
    p.id AS produto_id,
    p.nome AS produto,
    p.preco
FROM listas_diarias l
JOIN restaurantes r ON r.id = l.restaurante_id
JOIN lista_produtos lp ON lp.lista_diaria_id = l.id
JOIN produtos p ON p.id = lp.produto_id
WHERE l.status = 'ABERTA'
  AND l.horario_fechamento > NOW()
ORDER BY r.nome, p.nome;


-- ------------------------------------------------------------------------------
-- TESTE 2 (CU02): Criar um Pedido (Aluno ID 1 na Lista ID 1)
-- Insere o pedido e 2 itens com preço congelado (RN04)
-- ------------------------------------------------------------------------------
DO $$
DECLARE
    v_pedido_id BIGINT;
BEGIN
    -- 1. Cria o pedido
    INSERT INTO pedidos (lista_diaria_id, usuario_id, data_hora_pedido, valor_total, status, status_retirada)
    VALUES (1, 1, NOW(), 28.00, 'ATIVO', 'PENDENTE')
    RETURNING id INTO v_pedido_id;

    -- 2. Insere item 1 (1x Quentinha Frango - R$ 22.00)
    INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
    VALUES (v_pedido_id, 1, 1, 22.00);

    -- 3. Insere item 2 (1x Suco Natural - R$ 6.00)
    INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)
    VALUES (v_pedido_id, 3, 1, 6.00);

    RAISE NOTICE 'Pedido criado com sucesso! ID: %', v_pedido_id;
END $$;


-- ------------------------------------------------------------------------------
-- TESTE 3 (RN03 - Pedido Único Ativo):
-- Tentar criar um SEGUNDO pedido ATIVO para o mesmo Aluno 1 na mesma Lista 1
-- ESPERADO: O banco DEVE RECUSAR com erro:
-- "duplicate key value violates unique constraint uk_pedido_ativo"
-- ------------------------------------------------------------------------------
INSERT INTO pedidos (lista_diaria_id, usuario_id, data_hora_pedido, valor_total, status, status_retirada)
VALUES (1, 1, NOW(), 25.00, 'ATIVO', 'PENDENTE');


-- ------------------------------------------------------------------------------
-- TESTE 4 (CU03 / RN03): Cancelar o pedido existente
-- ------------------------------------------------------------------------------
UPDATE pedidos 
SET status = 'CANCELADO' 
WHERE usuario_id = 1 AND lista_diaria_id = 1 AND status = 'ATIVO';


-- ------------------------------------------------------------------------------
-- TESTE 5 (RN03): Tentar criar novo pedido APÓS o cancelamento
-- ESPERADO: Deve ter SUCESSO, pois o pedido cancelado não bloqueia o índice parcial!
-- ------------------------------------------------------------------------------
INSERT INTO pedidos (lista_diaria_id, usuario_id, data_hora_pedido, valor_total, status, status_retirada)
VALUES (1, 1, NOW(), 22.00, 'ATIVO', 'PENDENTE');


-- ------------------------------------------------------------------------------
-- TESTE 6 (RN05 - Integridade de Papel e Restaurante):
-- Tentar criar um ALUNO com restaurante_id não-nulo
-- ESPERADO: Erro de violação da constraint "ck_usuario_papel_restaurante"
-- ------------------------------------------------------------------------------
INSERT INTO usuarios (nome, email, senha_hash, telefone, papel, restaurante_id)
VALUES ('Aluno Invalido', 'invalido@impatech.edu.br', 'hash', '21999999999', 'ALUNO', 1);


-- ------------------------------------------------------------------------------
-- TESTE 7 (CU06 / RF05): Gerar Relatório de Produção para a Cozinha
-- Agrupa todos os pedidos ATIVOS por produto e soma as quantidades
-- ------------------------------------------------------------------------------
SELECT 
    p.id AS produto_id,
    p.nome AS produto,
    SUM(ip.quantidade) AS total_unidades,
    SUM(ip.quantidade * ip.preco_unitario) AS subtotal_geral
FROM pedidos ped
JOIN itens_pedido ip ON ip.pedido_id = ped.id
JOIN produtos p ON p.id = ip.produto_id
WHERE ped.lista_diaria_id = 1 
  AND ped.status = 'ATIVO'
GROUP BY p.id, p.nome
ORDER BY total_unidades DESC;
