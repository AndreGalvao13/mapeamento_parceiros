CREATE VIEW fornecedores_resumo AS
SELECT
    f.id,
    f.nome,
    f.contato,
    e.nome AS especialidade,
    COUNT(c.id) AS num_contratos,
    COALESCE(SUM(c.valor), 0) AS valor_total,
    COALESCE(AVG(c.valor), 0) AS valor_medio
FROM fornecedores f
LEFT JOIN contratos c ON c.fornecedor_id = f.id
LEFT JOIN especialidades e ON e.id = f.especialidade_id
GROUP BY f.id, f.nome, f.contato, e.nome;