INSERT INTO segmentos (nome)
VALUES ('saneamento');

INSERT INTO especialidades (nome)
VALUES ('financas');

INSERT INTO fornecedores (nome, contato, especialidade_id)
VALUES('CERES INTELIGENCIA FINANCEIRA', 'ceres@ceresinteligencia.com.br', 1);

INSERT INTO contratos (data, objeto, segmento_id, fornecedor_id, valor)
VALUES('2026-08-21', 'SERVICOS DE CONSULTORIA ECONOMICO-FINANCEIRA PARA DESESTATIZACAO DE EMPRESA X', 1, 1, 300000);

INSERT INTO contratos (data, objeto, segmento_id, fornecedor_id, valor)
VALUES('2026-08-21', 'SERVICOS DE CONSULTORIA TECNOLOGICA PARA EMPRESA X', Null, 1, 400000);

-- inserir testes invalidos 
-- 1. nome repetido
INSERT INTO fornecedores (nome, contato, especialidade_id)
VALUES('CERES INTELIGENCIA FINANCEIRA', 'ceres@gmail.com', 1);

--2. fornecedor inexsistente
INSERT INTO contratos (data, objeto, segmento_id,fornecedor_id, valor)
VALUES('2026-08-21', 'CONSULTORIA ESPECIALIZADA EM ENGENHARIA', 1, 2, 300000);

--3.contrato sem valor
INSERT INTO contratos (data, objeto, segmento_id,fornecedor_id)
VALUES('2026-08-21', 'CONSULTORIA ESPECIALIZADA EM JURIDICO', 1, 1);

