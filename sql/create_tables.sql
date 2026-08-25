CREATE TABLE segmentos(
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE especialidades(
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE fornecedores(
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    contato TEXT,
    especialidade_id INT references especialidades(id)
);

CREATE TABLE contratos(
    id SERIAL PRIMARY KEY,
    data DATE NOT NULL, 
    objeto TEXT NOT NULL,
    segmento_id INT references segmentos(id),
    fornecedor_id INT NOT NULL references fornecedores(id),
    valor NUMERIC(18,2) NOT NULL 
);
