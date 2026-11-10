-- Migração 001: renomeia o papel de usuário ALUNO -> CLIENTE.
--
-- Padroniza a terminologia dos atores em Cliente e Parceiro, conforme
-- decisão de projeto registrada no README (Glossário / Atores).
--
-- Idempotente: pode ser executada mais de uma vez sem efeito adicional.
-- Aplicar ANTES de subir a aplicação com o novo código, pois o domínio
-- passa a emitir 'CLIENTE' e o CHECK antigo rejeitaria o valor.

BEGIN;

-- 1. Remove os CHECKs que fixam o literal 'ALUNO'. O CHECK da coluna `papel`
--    é anônimo no schema.sql, então é localizado pelo catálogo em vez de pelo
--    nome, que o PostgreSQL gera automaticamente (usuarios_papel_check).
DO $$
DECLARE
    nome_constraint TEXT;
BEGIN
    FOR nome_constraint IN
        SELECT con.conname
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'usuarios'
          AND con.contype = 'c'
          AND pg_get_constraintdef(con.oid) LIKE '%ALUNO%'
    LOOP
        EXECUTE format('ALTER TABLE usuarios DROP CONSTRAINT %I', nome_constraint);
    END LOOP;
END $$;

-- 2. Converte os dados existentes.
UPDATE usuarios SET papel = 'CLIENTE' WHERE papel = 'ALUNO';

-- 3. Recria os CHECKs com o novo literal.
ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_papel_check
    CHECK (papel IN ('CLIENTE', 'PARCEIRO'));

-- RN05: Cliente não pode ter restaurante vinculado; Parceiro é obrigado a ter.
ALTER TABLE usuarios
    ADD CONSTRAINT ck_usuario_papel_restaurante CHECK (
        (papel = 'CLIENTE' AND restaurante_id IS NULL) OR
        (papel = 'PARCEIRO' AND restaurante_id IS NOT NULL)
    );

COMMIT;
