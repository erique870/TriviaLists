-- ==============================================================================
-- TRIVIALISTS - Schema do Banco de Dados (PostgreSQL / Supabase)
-- ==============================================================================

-- 1. Tabela: restaurantes
CREATE TABLE IF NOT EXISTS restaurantes (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    endereco VARCHAR(255) NOT NULL,
    horario_padrao_abertura TIME NOT NULL DEFAULT '08:00:00',
    horario_padrao_fechamento TIME NOT NULL DEFAULT '11:00:00',
    tipo_cardapio VARCHAR(20) NOT NULL CHECK (tipo_cardapio IN ('FIXO', 'VARIAVEL')),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Tabela: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    telefone VARCHAR(30) NOT NULL,
    papel VARCHAR(20) NOT NULL CHECK (papel IN ('ALUNO', 'PARCEIRO')),
    restaurante_id BIGINT REFERENCES restaurantes(id) ON DELETE RESTRICT,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- RN05: Aluno não pode ter restaurante vinculado; Parceiro é obrigado a ter
    CONSTRAINT ck_usuario_papel_restaurante CHECK (
        (papel = 'ALUNO' AND restaurante_id IS NULL) OR
        (papel = 'PARCEIRO' AND restaurante_id IS NOT NULL)
    )
);

-- 3. Tabela: produtos (Aqui é pra ir o catálogo permanente do restaurante)
CREATE TABLE IF NOT EXISTS produtos (
    id BIGSERIAL PRIMARY KEY,
    restaurante_id BIGINT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    nome VARCHAR(120) NOT NULL,
    descricao TEXT DEFAULT '',
    preco NUMERIC(10, 2) NOT NULL CHECK (preco >= 0),
    disponivel BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Tabela: listas_diarias
CREATE TABLE IF NOT EXISTS listas_diarias (
    id BIGSERIAL PRIMARY KEY,
    restaurante_id BIGINT NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
    data DATE NOT NULL,
    horario_abertura TIMESTAMPTZ NOT NULL,
    horario_fechamento TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA', 'FECHADA')),
    criada_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Fechamento deve ser posterior à abertura
    CONSTRAINT ck_lista_horarios CHECK (horario_fechamento > horario_abertura)
);

-- 5. Tabela associativa: lista_produtos (Produtos disponíveis na lista do dia, nao necessariamente todos)
CREATE TABLE IF NOT EXISTS lista_produtos (
    lista_diaria_id BIGINT NOT NULL REFERENCES listas_diarias(id) ON DELETE CASCADE,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    PRIMARY KEY (lista_diaria_id, produto_id)
);

-- Impede que uma lista de um restaurante inclua produto de outro restaurante.
CREATE OR REPLACE FUNCTION validar_restaurante_lista_produto()
RETURNS TRIGGER AS $$
DECLARE
    restaurante_lista BIGINT;
    restaurante_produto BIGINT;
BEGIN
    SELECT restaurante_id INTO restaurante_lista
      FROM listas_diarias WHERE id = NEW.lista_diaria_id;
    SELECT restaurante_id INTO restaurante_produto
      FROM produtos WHERE id = NEW.produto_id;
    IF restaurante_lista IS DISTINCT FROM restaurante_produto THEN
        RAISE EXCEPTION 'O produto deve pertencer ao restaurante da lista.'
          USING ERRCODE = '23514', CONSTRAINT = 'ck_lista_produto_mesmo_restaurante';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_lista_produto_mesmo_restaurante ON lista_produtos;
CREATE TRIGGER trg_lista_produto_mesmo_restaurante
BEFORE INSERT OR UPDATE OF lista_diaria_id, produto_id ON lista_produtos
FOR EACH ROW EXECUTE FUNCTION validar_restaurante_lista_produto();

-- 6. Tabela: pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id BIGSERIAL PRIMARY KEY,
    lista_diaria_id BIGINT NOT NULL REFERENCES listas_diarias(id) ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    data_hora_pedido TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valor_total NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (valor_total >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'CANCELADO')),
    status_retirada VARCHAR(20) NOT NULL DEFAULT 'PENDENTE' CHECK (status_retirada IN ('PENDENTE', 'RETIRADO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. Tabela: itens_pedido
CREATE TABLE IF NOT EXISTS itens_pedido (
    id BIGSERIAL PRIMARY KEY,
    pedido_id BIGINT NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id BIGINT NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario NUMERIC(10, 2) NOT NULL CHECK (preco_unitario >= 0) -- RN04
);

-- Impede que um item de pedido use produto ausente do cardápio daquela lista.
CREATE OR REPLACE FUNCTION validar_item_pedido_no_cardapio()
RETURNS TRIGGER AS $$
DECLARE
    lista_id BIGINT;
BEGIN
    SELECT lista_diaria_id INTO lista_id FROM pedidos WHERE id = NEW.pedido_id;
    IF NOT EXISTS (
        SELECT 1 FROM lista_produtos
         WHERE lista_diaria_id = lista_id AND produto_id = NEW.produto_id
    ) THEN
        RAISE EXCEPTION 'O produto não pertence ao cardápio do pedido.'
          USING ERRCODE = '23514', CONSTRAINT = 'ck_item_pedido_no_cardapio';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_item_pedido_no_cardapio ON itens_pedido;
CREATE TRIGGER trg_item_pedido_no_cardapio
BEFORE INSERT OR UPDATE OF pedido_id, produto_id ON itens_pedido
FOR EACH ROW EXECUTE FUNCTION validar_item_pedido_no_cardapio();

-- ==============================================================================
-- PERFORMANCE E INTEGRIDADE DE NEGÓCIO
-- ==============================================================================

-- RN03: Restrição de unicidade parcial para garantir que cada aluno só tenha 1 pedido ATIVO por lista.
-- Se o pedido for cancelado o índice ignora e permite novo pedido.
CREATE UNIQUE INDEX IF NOT EXISTS uk_pedido_ativo 
ON pedidos (usuario_id, lista_diaria_id) 
WHERE (status = 'ATIVO');

-- Índice para CU01: Consulta de listas abertas
CREATE INDEX IF NOT EXISTS idx_listas_abertas 
ON listas_diarias (status, horario_fechamento);

-- Índice de busca de pedidos por usuário e lista
CREATE INDEX IF NOT EXISTS idx_pedidos_usuario_lista 
ON pedidos (usuario_id, lista_diaria_id);
