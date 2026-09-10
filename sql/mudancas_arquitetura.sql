ALTER TABLE contratos ADD COLUMN fonte_id INT references fontes(id);

ALTER TABLE contratos DROP CONSTRAINT contratos_pkey;

ALTER TABLE contratos
    ALTER COLUMN id SET NOT NULL,

ALTER TABLE contratos
    ADD CONSTRAINT contratos_pkey PRIMARY KEY (id, fornecedor_id, fonte_id);    

ALTER TABLE contratos
RENAME COLUMN id TO codigo;

ALTER TABLE contratos 
ALTER COLUMN codigo TYPE TEXT;