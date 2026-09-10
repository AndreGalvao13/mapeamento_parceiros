import csv
import time
from datetime import date
import requests
from bs4 import BeautifulSoup

URL_BASE = 'https://www.ungm.org'
#FORMATO DE DATA EXIGIDO PELO SITE: DD-MMM-AAAA (ex: 01-Jan-2017)
DATA_INICIAL = '01-Jan-2017'
DATA_FINAL = date.today().strftime('%d-%b-%Y')
#MUDE SEMPRE A VERSAO PARA NAO PERDER OS DADOS HISTORICOS
CSV_SAIDA = '../ONU/dados/contratos_onu_V3.csv'

#IDs internos do UNGM (data-unspscid), nao o codigo UNSPSC em si.
#Ajuste/complete essa lista conforme as categorias de servico que fizerem sentido.
UNSPSC_IDS = [
    107364,  # 80100000 - Management advisory services
    107365,  # 80110000 - Human resources services
    107366,  # 80120000 - Legal services
    107367,  # 80130000 - Real estate services
    107368,  # 80140000 - Marketing and distribution
    107369,  # 80150000 - Trade policy and services
    107370,  # 80160000 - Business administration services
    178271,  # 80170000 - Public relations and professional communications services
    107372,  # 81100000 - Professional engineering services
    107373,  # 81110000 - Computer services
    107374,  # 81120000 - Economics
    107375,  # 81130000 - Statistics
    107379,  # 81140000 - Manufacturing technologies
    107382,  # 81150000 - Earth science services
    145204,  # 81160000 - Information Technology Service Delivery
    178325,  # 81170000 - Biological science services
    107391,  # 83100000 - Utilities
    107392,  # 83110000 - Telecommunications media services
    107395,  # 83120000 - Information services
]

#ID interno de pais no UNGM (mesmo usado em Countries e SupplierCountries).
BRASIL_ID = 2320

PAGE_SIZE = 15
PAUSA_ENTRE_REQUISICOES = 1
MAX_TENTATIVAS = 5


def abrir_sessao():
    sessao = requests.Session()
    sessao.headers.update({'User-Agent': 'Mozilla/5.0'})
    sessao.get(f'{URL_BASE}/Public/ContractAward')
    return sessao


def requisitar_com_retry(func, *args, **kwargs):
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        resposta = func(*args, **kwargs)
        if resposta.status_code != 429:
            resposta.raise_for_status()
            return resposta
        espera = int(resposta.headers.get('Retry-After', 10)) * tentativa
        print(f'429 recebido, aguardando {espera}s antes de tentar novamente (tentativa {tentativa}/{MAX_TENTATIVAS})...')
        time.sleep(espera)
    resposta.raise_for_status()
    return resposta


def buscar_pagina(sessao, page_index, countries=None, supplier_countries=None):
    payload = {
        'PageIndex': page_index,
        'PageSize': PAGE_SIZE,
        'Title': '', 'Description': '', 'Reference': '', 'Supplier': '', 'UngmNumber': None,
        'AwardFrom': DATA_INICIAL, 'AwardTo': DATA_FINAL,
        'Countries': countries or [], 'SupplierCountries': supplier_countries or [], 'Agencies': [],
        'UNSPSCs': UNSPSC_IDS,
        'SortField': 'AwardDate', 'SortAscending': False,
    }
    resposta = requisitar_com_retry(
        sessao.post,
        f'{URL_BASE}/Public/ContractAward/PublicSearch',
        json=payload,
        headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': f'{URL_BASE}/Public/ContractAward'},
    )
    return resposta.text


def extrair_registros(html):
    soup = BeautifulSoup(html, 'html.parser')
    linhas = soup.find_all('div', class_='dataRow')
    registros = []
    for linha in linhas:
        celulas = linha.find_all('div', class_='tableCell', recursive=False)
        titulo = celulas[0].find(class_='ungm-title')
        registros.append({
            'codigo': linha['data-contractawardid'],
            'objeto': titulo.get_text(strip=True) if titulo else celulas[0].get_text(strip=True),
            'nome': celulas[1].get_text(strip=True),
            'data': celulas[2].get_text(strip=True),
            'agencia': celulas[3].get_text(strip=True),
            'referencia': celulas[4].get_text(strip=True),
            'pais': celulas[5].get_text(strip=True),
        })
    return registros


def buscar_detalhe(sessao, contract_id):
    resposta = requisitar_com_retry(sessao.get, f'{URL_BASE}/Public/ContractAward/Popup/{contract_id}')
    soup = BeautifulSoup(resposta.text, 'html.parser')

    rotulo = soup.find('label', attrs={'for': 'ContractValue'})
    valor_span = rotulo.find_next('span', class_='value') if rotulo else None
    valor = valor_span.get_text(strip=True) if valor_span else None

    #Contratos em consorcio tem mais de um fornecedor aqui; a listagem os concatena sem separador.
    container = soup.find('div', id='contractAwardVendorsContainer')
    fornecedores = [label.get_text(strip=True) for label in container.find_all('label')] if container else []

    return valor, fornecedores


def montar_csv(registros, caminho_csv):
    if not registros:
        print('Nenhum registro encontrado.')
        return
    colunas = list(registros[0].keys())
    with open(caminho_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=colunas, restval='')
        writer.writeheader()
        writer.writerows(registros)


def buscar_todos_registros(sessao, countries=None, supplier_countries=None):
    registros = []
    page_index = 0
    while True:
        html = buscar_pagina(sessao, page_index, countries, supplier_countries)
        pagina = extrair_registros(html)
        if not pagina:
            break
        print(f'Pagina {page_index}: {len(pagina)} registros encontrados.')
        registros.extend(pagina)
        page_index += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)
    return registros


def main():
    sessao = abrir_sessao()

    print('Buscando contratos com execucao no Brasil...')
    registros_execucao = buscar_todos_registros(sessao, countries=[BRASIL_ID])

    print('Buscando contratos com fornecedor do Brasil...')
    registros_fornecedor = buscar_todos_registros(sessao, supplier_countries=[BRASIL_ID])

    #Une os dois resultados por codigo, removendo duplicatas (contratos que aparecem nas duas buscas).
    registros_por_codigo = {r['codigo']: r for r in registros_execucao + registros_fornecedor}
    todos_registros = list(registros_por_codigo.values())
    print(f'{len(todos_registros)} registros unicos (execucao ou fornecedor no Brasil).')

    linhas_finais = []
    i = 1
    for registro in todos_registros:
        valor, fornecedores = buscar_detalhe(sessao, registro['codigo'])
        if not fornecedores:
            fornecedores = [registro['nome']]
        for nome_fornecedor in fornecedores:
            linha = dict(registro)
            linha['nome'] = nome_fornecedor
            linha['valor'] = valor
            linhas_finais.append(linha)
        print(f'registro {i} processado')
        i += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)

    montar_csv(linhas_finais, CSV_SAIDA)
    print(f'CSV gerado em: {CSV_SAIDA}')


if __name__ == '__main__':
    main()
