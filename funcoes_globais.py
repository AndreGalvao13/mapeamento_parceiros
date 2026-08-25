import pandas as pd
import unicodedata
import glob
import re
from dotenv import load_dotenv
import psycopg2 as pg
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
import os
import requests
from datetime import datetime, timedelta

MAPEAMENTO_NOMES = {
    "VERNALHA GUIMARAES PEREIRA E PETIAN SOCIEDADE DE ADVOGADOS" : "VERNALHA PEREIRA ADVOGADOS",
    "WAY CARBON" : "WAYCARBON SOLUCOES AMBIENTAIS E PROJETOS DE CARBONO LTDA",
    "UNIVERSIDADE FEDERAL DA BAHIA" : "UNIVERSIDADE FEDERAL DA BAHIA (UFBA)",
    "TELECO" : "TELECO INFORMACAO E SERVICOS DE TELECOMUNICACOES LTDA",
    "RADAR PPP LTDA BRAZIL" : "RADAR PPP LTDA",
    "PEZCO ECONOMIC & FINANCIAL ANALYSIS" : "PEZCO CONSULTORIA EDITORA E DESENVOLVIMENTO LTDA",
    "PRICEWATERHOUSECOOPERS CORPORATE FINANCE & RECOVERY LTDA" : "PRICEWATERHOUSECOOPERS SERVICOS PROFISSIONAIS LTDA",
    "PLANOS ENGENHARIA S/S LTDA" : "PLANOS ENGENHARIA",
    "PEERS" : "PEERS CONSULTORIA E SERVICOS LTDA",
    "NUMERIK" : "NUMERIK CONSULTORIA EM GESTAO LTDA",
    "NAVARRO PRADO NEFUSSI MANDEL & SANTOS SILVA ADVOGADOS" : "NAVARRO PRADO NEFUSSI MANDEL E SANTOS SILVA ADVOGADOS",
    "NATURAL INTELLIGENCE (NINT)" : "NATURAL INTELLIGENCE LTDA",
    "MITSIDI PROJETOS" : "MITSIDI SERVICOS E PROJETOS LTDA",
    "MADRONA ADVOGADOS" : "MADRONA SOCIEDADE DE ADVOGADOS",
    "MACROPLAN" : "MACROPLAN PROSPECTIVA ESTRATEGIA E GESTAO S S LTDA",
    "MACROPLAN PROSPECTIVA ESTRATAGIA E GESTAO S S LTDA" : "MACROPLAN PROSPECTIVA ESTRATEGIA E GESTAO S S LTDA",
    "MACHADO MEYER SENDACZ E OPICE ADVOGADOS" : "MACHADO MEYER SENDACZ OPICE E ANDRADE ADVOGADOS",
    "KOAN FINANCAS SUSTENTAVEIS LTDA" : "KOAN FINANCAS SUSTENTAVEIS LTDA (SITAWI)",
    "KOAN FINANCAS SUSTENTAVEIS LTDA AKA SITAWI" : "KOAN FINANCAS SUSTENTAVEIS LTDA (SITAWI)",
    "JGP CONSULTORIA E PARTICIPACIONES LTDA" : "JGP CONSULTORIA E PARTICIPACOES LTDA",
    "JPG CONSULTORIA E PARTICIPACOES LTDA" : "JGP CONSULTORIA E PARTICIPACOES LTDA",
    "FUNCACAO GETULIO VARGAS" : "FUNDACAO GETULIO VARGAS FGV",
    "FUNDACAO GETULIO VARGAS FGV BRAZIL" : "FUNDACAO GETULIO VARGAS FGV",
    "AGROICONE": "AGROICONE LTDA",
    "B2ML SISTEMAS": "B2ML SISTEMAS LTDA",
    "DIREITO AGIL SOLUCOES EM TECNOLOGIA E INOVACAO LTD": "DIREITO AGIL SOLUCOES EM TECNOLOGIA E INOVACAO LTDA",
    "DYNATEST ENGENHARIA": "DYNATEST ENGENHARIA LTDA",
    "RADAR PPP": "RADAR PPP LTDA",
    "TRACTEBEL ENGINEERING SA": "TRACTEBEL ENGINEERING LTDA",
    "WAYCARBON SOLUCOES AMBIENTAIS E PROJETOS DE CARBONO SA": "WAYCARBON SOLUCOES AMBIENTAIS E PROJETOS DE CARBONO LTDA",
}

def cotacao_dolar(data):  # data como datetime/date, não string
    dados = []
    while not dados:
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            f"CotacaoDolarDia(dataCotacao='{data.strftime('%m-%d-%Y')}')?$format=json"
        )
        resposta = requests.get(url)
        resposta.raise_for_status()
        dados = resposta.json()['value']
        if not dados:
            data = data - timedelta(days=1)
    return dados[0]['cotacaoVenda']

def get_connection():
    load_dotenv(dotenv_path='../config/.env')
    connection = pg.connect(
        host='aws-0-us-west-2.pooler.supabase.com',
        dbname='postgres',
        user='postgres.jqucvxtwfvoglbvzonba',
        password=os.environ['DATABASE_KEY']
    )
    return connection

def get_cursor(connection):
    return connection.cursor()

def get_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        username="postgres.jqucvxtwfvoglbvzonba", 
        password=os.environ['DATABASE_KEY'],
        host="aws-0-us-west-2.pooler.supabase.com",
        port=5432,
        database="postgres",
    )
    return create_engine(url)

def normalizar_texto(df, coluna, mapeamento=None):
    df[coluna] = (
        df[coluna]
        .astype(str)
        .apply(lambda x: unicodedata.normalize("NFD", x))
        .str.encode("ascii", "ignore")
        .str.decode("utf-8")
        .str.upper()
        .str.replace(",", "", regex=False)
        .str.replace("-", " ", regex=False)
        .str.replace(".", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    
    if mapeamento:
        df[coluna] = df[coluna].replace(mapeamento)
    
    return df

def load_fornecedores_table(connection, cursor, df):
    try:
        i=0
        for _, linha in df.iterrows():
            cursor.execute(
                "INSERT INTO fornecedores (nome, contato, especialidade_id) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING",
                (
                    linha['nome'],
                    None if pd.isna(linha['contato']) else linha['contato'],
                    None if pd.isna(linha['especialidade_id']) else linha['especialidade_id'],
                )
            )
            print(f'fornecedor {i} processado')
            i += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise

def load_contratos_table(connection, cursor,df):
    cursor.execute("SELECT 1 FROM pg_constraint WHERE conname = 'contratos_unicos'")
    if cursor.fetchone() is None:
        cursor.execute(
            "ALTER TABLE contratos ADD CONSTRAINT contratos_unicos UNIQUE (fornecedor_id, data, valor, objeto)"
        )
        connection.commit()

    try:
        i = 1
        for _, linha in df.iterrows():
            cursor.execute(
                "INSERT INTO contratos (data, objeto, segmento_id, fornecedor_id, valor) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (fornecedor_id, data, valor, objeto) DO NOTHING",
                (
                    linha['data'],
                    linha['objeto'],
                    None if pd.isna(linha['segmento_id']) else linha['segmento_id'],
                    linha['fornecedor_id'],
                    linha['valor'],
                )
            )
            print(f'contrato {i} processado')
            i += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise

def end_db_connection(cursor, connection):
    cursor.close()
    connection.close()

def get_arquivo_recente(fonte):
    def extrair_versao(caminho):
        match = re.search(r'_V(\d+)\.(csv|xlsx)$', caminho)
        return int(match.group(1)) if match else -1
    if fonte.upper() == 'BNDES':
        pattern = '../BNDES/dados/contratos_bndes_V*.csv'
        reader = pd.read_csv
        extension = '.csv'
    elif fonte.upper() == 'IADB':
        pattern = '../IADB/dados/contratacoes_IADB_V*.xlsx'
        reader = pd.read_excel
        extension = '.xlsx'
    else:
        raise ValueError(f"Fonte '{fonte}' não reconhecida. Use 'BNDES' ou 'IADB'")
    arquivos = glob.glob(pattern)
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para '{fonte}' em {pattern}")
    arquivo_mais_recente = max(arquivos, key=extrair_versao)
    print(f'✓ Lendo arquivo mais recente: {arquivo_mais_recente}')
    
    return reader(arquivo_mais_recente)
