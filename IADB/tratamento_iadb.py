import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import funcoes_globais as fg
from funcoes_globais import MAPEAMENTO_NOMES
import pandas as pd

connection = fg.get_connection()
cursor = fg.get_cursor(connection)
engine = fg.get_engine()
df = fg.get_arquivo_recente('IADB')

colunas_para_manter = ['Award Date', 'Contract Description', 'Vendor', 'Contract Amount']
df_filtrado = df[colunas_para_manter]
mapeamento = {'Award Date' : 'data', 'Contract Description' : 'objeto', 'Vendor' : 'nome', 'Contract Amount' : 'valor'}
df_filtrado = df_filtrado.rename(columns = mapeamento)
df_filtrado['valor'] = df_filtrado['valor'].astype(float)
df_filtrado['data'] = pd.to_datetime(df_filtrado['data'],format="%d/%m/%Y")
df_filtrado = fg.normalizar_texto(df_filtrado,'objeto',)
df_filtrado = fg.normalizar_texto(df_filtrado,'nome', MAPEAMENTO_NOMES)
df_filtrado['segmento'] = None
df_filtrado['valor'] = df_filtrado.apply(
    lambda linha: linha['valor'] * fg.cotacao_dolar(linha['data']),
    axis=1
)
df_empresas = pd.DataFrame(df_filtrado['nome'].unique(), columns=['nome'])
df_empresas['contato'] = None
df_empresas['especialidade_id'] = None

fg.load_fornecedores_table(connection, cursor, df_empresas)

df_fornecedores_atualizada = pd.read_sql("SELECT * FROM fornecedores", engine)
existentes = df_empresas.merge(df_fornecedores_atualizada[['id', 'nome']], on='nome', how='inner')
nova_ordem = ['id','nome']
existentes = existentes[nova_ordem]
df_concatenado = df_filtrado.merge(existentes, on='nome')

nao_casaram = set(df_filtrado['nome']) - set(existentes['nome'])
if nao_casaram:
    print(f'Aviso: {len(nao_casaram)} fornecedor(es) do CSV nao foram encontrados na tabela fornecedores e serao ignorados:')
    for nome in nao_casaram:
        print(f'  - {nome}')

df_concatenado = df_concatenado.rename(columns={'id' : 'fornecedor_id','segmento' : 'segmento_id'})
colunas_para_manter_concatenado = ['data', 'objeto', 'segmento_id','fornecedor_id','valor']
df_concatenado = df_concatenado[colunas_para_manter_concatenado]
df_concatenado['segmento_id'] = None

fg.load_contratos_table(connection, cursor, df_concatenado)
fg.end_db_connection(cursor, connection)
