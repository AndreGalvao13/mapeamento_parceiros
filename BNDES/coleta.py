import time
import csv
from datetime import date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#USE COMO DATA INICIAL UM DIA APOS AS INFORMAÇÕES QUE TEMOS EM BANCO
URL = 'https://www.bndes.gov.br/wps/portal/site/home/transparencia/desestatizacao/contratos-desestatizacao'
DATA_INICIAL = '2017-01-01'
DATA_FINAL = str(date.today())
#MUDE SEMPRE A VERSAO PARA NAO PERDER OS DADOS HISTORICOS
CSV_SAIDA = '..BNDES/dados/contratos_bndes_V02.csv'

JS_CONTAR_LINHAS = """
    const host = document.querySelector('bndes-data-search-desestat');
    if (!host) return -1;
    const shadowB = host.shadowRoot.querySelector('bndes-data-visualization-nivel');
    if (!shadowB) return -1;
    const shadowC = shadowB.shadowRoot.querySelector('bndes-tabela-nivel');
    if (!shadowC) return -1;
    return shadowC.shadowRoot.querySelectorAll('div.linha').length;
"""

JS_EXTRAIR_REGISTROS = """
    const host = document.querySelector('bndes-data-search-desestat');
    const shadowB = host.shadowRoot.querySelector('bndes-data-visualization-nivel').shadowRoot;
    const shadowC = shadowB.querySelector('bndes-tabela-nivel').shadowRoot;
    const linhas = shadowC.querySelectorAll('div.linha');
    const out = [];
    linhas.forEach(linha => {
        const grupo = linha.querySelector('.tituloRegistro');
        const registro = {grupo: grupo ? grupo.textContent.trim() : ''};
        linha.querySelectorAll(':scope > span.celula').forEach(celula => {
            const rotulo = celula.querySelector('span');
            const valor = celula.querySelector('span.texto[style*="cor-texto-campo"]');
            if (rotulo && valor) {
                registro[rotulo.textContent.trim()] = valor.textContent.trim();
            }
        });
        out.push(registro);
    });
    return out;
"""


def set_date(driver, elemento, iso_date):  # iso_date ex: '2017-01-01'
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
        "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
        elemento, iso_date
    )


def esperar_tabela_estabilizar(driver, timeout=60, intervalo=1.5):
    inicio = time.time()
    ultima_contagem = -1
    estavel_desde = None
    while time.time() - inicio < timeout:
        contagem = driver.execute_script(JS_CONTAR_LINHAS)
        if contagem > 0:
            if contagem == ultima_contagem:
                if estavel_desde is None:
                    estavel_desde = time.time()
                elif time.time() - estavel_desde > intervalo:
                    return contagem
            else:
                estavel_desde = None
            ultima_contagem = contagem
        time.sleep(intervalo)
    return ultima_contagem


def montar_csv_completo(registros, caminho_csv):
    todas_colunas = []
    for r in registros:
        for k in r.keys():
            if k not in todas_colunas:
                todas_colunas.append(k)

    ultimo_contexto = {}
    registros_completos = []
    for r in registros:
        if r.get('grupo') != ultimo_contexto.get('grupo'):
            ultimo_contexto = {}
        linha_completa = {**ultimo_contexto, **r}
        registros_completos.append(linha_completa)
        ultimo_contexto = linha_completa

    with open(caminho_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=todas_colunas, restval='')
        writer.writeheader()
        writer.writerows(registros_completos)


def main():
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 10)
    try:
        driver.get(URL)

        host = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'bndes-data-search-desestat')))
        shadow = host.shadow_root

        data_inicial = wait.until(lambda d: shadow.find_element(By.ID, 'dataMaior'))
        data_final = shadow.find_element(By.ID, 'dataMenor')

        set_date(driver, data_inicial, DATA_INICIAL)
        set_date(driver, data_final, DATA_FINAL)

        total_linhas = esperar_tabela_estabilizar(driver)
        print(f'Tabela carregada com {total_linhas} linhas.')

        registros = driver.execute_script(JS_EXTRAIR_REGISTROS)
        print(f'{len(registros)} registros extraidos.')

        montar_csv_completo(registros, CSV_SAIDA)
        print(f'CSV gerado em: {CSV_SAIDA}')
    finally:
        driver.quit()


if __name__ == '__main__':
    main()