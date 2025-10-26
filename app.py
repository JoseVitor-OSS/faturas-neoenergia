import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import time
import base64
import requests
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib.parse import urlencode
import zipfile
import io
import sys 

# 🚨 SOLUÇÃO DE EMERGÊNCIA - Forçar Streamlit
if __name__ == "__main__" and not any("streamlit" in arg for arg in sys.argv):
    print("🔧 FORÇANDO STREAMLIT RUN...")
    os.execvp("streamlit", ["streamlit", "run", __file__, "--server.port=8000", "--server.address=0.0.0.0"])

print("✅ STREAMLIT INICIADO CORRETAMENTE!")
# === CONFIGURAÇÃO DE RETRY === 
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos
RETRY_BACKOFF = 1.5
MAX_DELAY = 30

# Erros que NÃO devem ter retry
ERRORS_SEM_RETRY = [
    "fatura indisponível no canal digital",
    "fatura não disponível",
    "documento não relacionado",
    "acesso negado",
    "não encontrado"
]

# ----------------------------
# Configurações iniciais
# ----------------------------
st.set_page_config(page_title="Sistema de Faturas Neoenergia", layout="wide")

# Aplicar cores personalizadas
st.markdown("""
<style>
/* ===== Fundo geral ===== */
.main, .stApp {
    background-color: #02231C !important;
    color: #FFFFFF !important;
}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"], .stSidebar {
    background-color: #011A14 !important;
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
}

/* ===== Textos gerais ===== */
h1, h2, h3, h4, h5, h6,
.stMarkdown, .stText, p, label, span, div {
    color: #FFFFFF !important;
}

/* ===== Campos de input ===== */
input, textarea, select {
    background-color: #03382C !important;
    color: #FFFFFF !important;
    border: 1px solid #00FF88 !important;
    border-radius: 6px !important;
}

/* ===== DROPDOWN / SELECTBOX ===== */
/* Barra de seleção */
div[data-baseweb="select"] > div:first-child {
    background-color: #03382C !important;
    color: #FFFFFF !important;
    border: 1px solid #00FF88 !important;
    border-radius: 6px !important;
}

/* Texto dentro da barra */
div[data-baseweb="select"] input {
    background-color: #03382C !important;
    color: #FFFFFF !important;
}

/* Popover (container flutuante) e Listbox (lista interna) */
div[data-baseweb="popover"], 
div[role="listbox"] {
    background-color: #03382C !important;
}

/* Borda específica do popover */
div[data-baseweb="popover"] {
    border: 1px solid #00FF88 !important;
}

/* Itens da lista suspensa (genérico para 'li' ou 'div') */
[data-baseweb="option"], [role="option"] {
    background-color: #03382C !important;
    color: #A7FFD9 !important;
}

/* Hover nos itens (genérico) */
[data-baseweb="option"]:hover, [role="option"]:hover {
    background-color: #00FF88 !important;
    color: #02231C !important;
}

/* Item selecionado (genérico) */
[data-baseweb="option"][aria-selected="true"], [role="option"][aria-selected="true"] {
    background-color: #00CC6A !important;
    color: #02231C !important;
}

/* ===== Botões ===== */
.stButton>button {
    background-color: #00FF88 !important;
    color: #02231C !important;
    font-weight: bold !important;
    border: none !important;
    border-radius: 8px !important;
}
.stButton>button:hover {
    background-color: #00CC6A !important;
    color: #02231C !important;
}

/* ===== Tabelas / DataFrames ===== */
.stDataFrame, .stTable, .dataframe {
    background-color: #03382C !important;
    color: #FFFFFF !important;
}
.stDataFrame table td, .stDataFrame table th {
    color: #FFFFFF !important;
}

/* ===== Mensagens ===== */
.stSuccess { color: #00FF88 !important; }
.stInfo { color: #A7FFD9 !important; }
.stWarning { color: #FFAA00 !important; }
.stError { color: #FF4444 !important; }

/* ===== Barras de progresso ===== */
.stProgress > div > div > div > div {
    background-color: #00FF88;
}

/* ===== Textos secundários ===== */
.stCaption, .stMarkdown small {
    color: #A7FFD9 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🏭 Sistema de Extração de Faturas Neoenergia")

# ----------------------------
# Variável global para controle de execução
# ----------------------------
if 'executando' not in st.session_state:
    st.session_state.executando = False
if 'parar_execucao' not in st.session_state:
    st.session_state.parar_execucao = False
if 'arquivos_baixados' not in st.session_state:
    st.session_state.arquivos_baixados = {}

# ----------------------------
# Função para criar arquivo ZIP
# ----------------------------
def criar_zip_pdfs(diretorio_base):
    """Cria um arquivo ZIP com todos os PDFs baixados"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(diretorio_base):
            for file in files:
                if file.endswith('.pdf'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, diretorio_base)
                    zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return zip_buffer

# ----------------------------
# Função para listar arquivos PDF baixados
# ----------------------------
def listar_pdfs_baixados(diretorio_base):
    """Lista todos os PDFs baixados organizados por mês"""
    pdfs_por_mes = {}
    
    if os.path.exists(diretorio_base):
        for mes_dir in os.listdir(diretorio_base):
            mes_path = os.path.join(diretorio_base, mes_dir)
            if os.path.isdir(mes_path):
                pdfs_mes = []
                for file in os.listdir(mes_path):
                    if file.endswith('.pdf'):
                        file_path = os.path.join(mes_path, file)
                        pdfs_mes.append({
                            'nome': file,
                            'caminho': file_path,
                            'tamanho': os.path.getsize(file_path)
                        })
                if pdfs_mes:
                    pdfs_por_mes[mes_dir] = pdfs_mes
    
    return pdfs_por_mes

# ----------------------------
# Função para exibir seção de downloads
# ----------------------------
def exibir_secao_downloads():
    """Exibe a seção com os arquivos baixados para download"""
    diretorio_base = "Neoenergia"
    
    if not os.path.exists(diretorio_base):
        st.info("📁 Nenhum arquivo baixado ainda.")
        return
    
    pdfs_por_mes = listar_pdfs_baixados(diretorio_base)
    
    if not pdfs_por_mes:
        st.info("📁 Nenhum arquivo PDF encontrado.")
        return
    
    st.subheader("📥 Arquivos Baixados")
    
    total_arquivos = sum(len(pdfs) for pdfs in pdfs_por_mes.values())
    total_tamanho = sum(
        pdf['tamanho'] 
        for mes_pdfs in pdfs_por_mes.values() 
        for pdf in mes_pdfs
    ) / (1024 * 1024)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Arquivos", total_arquivos)
    with col2:
        st.metric("Meses com Faturas", len(pdfs_por_mes))
    with col3:
        st.metric("Tamanho Total", f"{total_tamanho:.2f} MB")
    
    if total_arquivos > 0:
        zip_buffer = criar_zip_pdfs(diretorio_base)
        
        st.download_button(
            label="📦 Baixar Todos os Arquivos (ZIP)",
            data=zip_buffer,
            file_name=f"faturas_neoenergia_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
            mime="application/zip",
            use_container_width=True
        )
    
    for mes, pdfs in pdfs_por_mes.items():
        with st.expander(f"📅 Mês: {mes} ({len(pdfs)} arquivos)"):
            for pdf in pdfs:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"`{pdf['nome']}`")
                with col2:
                    st.write(f"{pdf['tamanho'] / 1024:.1f} KB")
                with col3:
                    with open(pdf['caminho'], 'rb') as f:
                        st.download_button(
                            label="📄 Baixar",
                            data=f,
                            file_name=pdf['nome'],
                            mime="application/pdf",
                            key=f"btn_{pdf['nome']}"
                        )

# ----------------------------
# Função de autenticação Google Sheets
# ----------------------------
def autorizar_google():
    """Autenticação simples com Service Account"""
    try:
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            service_account_info = dict(st.secrets['gcp_service_account'])
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets", 
                       "https://www.googleapis.com/auth/drive"]
            )
            gc = gspread.authorize(creds)
            return gc
        else:
            st.error("🔐 Credenciais não encontradas nos Secrets")
            return None
            
    except Exception as e:
        st.error(f"❌ Erro na autenticação: {e}")
        return None

# ----------------------------
# Configuração do Selenium
# ----------------------------
def iniciar_navegador(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        st.error(f"Erro ao iniciar navegador: {e}")
        return None

# ----------------------------
# Função para fazer requisições com retry
# ----------------------------
def fazer_requisicao_com_retry(url, headers=None, params=None, method='GET', 
                                 max_retries=MAX_RETRIES, 
                                 initial_delay=RETRY_DELAY,
                                 backoff_factor=RETRY_BACKOFF,
                                 skip_retry_errors=None):
    if skip_retry_errors is None:
        skip_retry_errors = ERRORS_SEM_RETRY
    
    for attempt in range(max_retries):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=90)
            else:
                response = requests.post(url, headers=headers, json=params, timeout=90)
            
            if response.status_code == 200:
                return response
            
            response_text = response.text.lower()
            should_skip_retry = any(error in response_text for error in skip_retry_errors)
            
            if should_skip_retry:
                return response
            
            if response.status_code == 500:
                current_delay = min(initial_delay * (backoff_factor ** attempt), MAX_DELAY)
                if attempt < max_retries - 1:
                    time.sleep(current_delay)
                    continue
                else:
                    return response
            
            return response
            
        except requests.exceptions.Timeout:
            current_delay = min(initial_delay * (backoff_factor ** attempt), MAX_DELAY)
            if attempt < max_retries - 1:
                time.sleep(current_delay)
                continue
            else:
                raise
        except requests.exceptions.ConnectionError:
            current_delay = min(initial_delay * (backoff_factor ** attempt), MAX_DELAY)
            if attempt < max_retries - 1:
                time.sleep(current_delay)
                continue
            else:
                raise
    
    return None

# ----------------------------
# Função para verificar token no storage
# ----------------------------
def verificar_token_storage(navegador, id_distribuidora):
    try:
        if id_distribuidora == 52:
            token_raw = navegador.execute_script("return window.localStorage.getItem('tokenNeSe');")
            return token_raw is not None
        else:
            token = navegador.execute_script("return window.localStorage.getItem('access_token') || window.localStorage.getItem('token');")
            return token is not None
    except:
        return False

# ----------------------------
# Função para limpar documento
# ----------------------------
def limpar_documento(documento):
    return re.sub(r'[^0-9]', '', documento)

# ----------------------------
# Função para parar execução
# ----------------------------
def parar_execucao():
    st.session_state.parar_execucao = True
    st.session_state.executando = False

# ----------------------------
# Função principal do scraper
# ----------------------------
def executar_scraper(df_filtrado, progress_bar, status_text, meses_desejados, mes_atraso, headless=False):
    diretorio_download = "Neoenergia"
    
    navegador = iniciar_navegador(headless)
    if not navegador:
        st.error("❌ Não foi possível iniciar o navegador")
        return None
    
    ucs_retidas = []
    tempos_ucs = []
    ucs_inativas = []
    ucs_sem_fatura = []
    ucs_cadastro_invalido = []
    ucs_ativar_cadastro = []
    ucs_fatura_indisponivel = []
    ucs_erro_sistema = []
    ucs_erro_busca = []
    ucs_sucesso = []
    
    tempo_total_inicio = time.perf_counter()
    os.makedirs(diretorio_download, exist_ok=True)
    
    for i in range(len(df_filtrado)):
        if st.session_state.parar_execucao:
            st.warning("⏹️ Execução interrompida pelo usuário")
            break

        inicio_uc = time.perf_counter()
        progress = (i + 1) / len(df_filtrado)
        progress_bar.progress(progress)
        status_text.text(f"Processando UC {i+1} de {len(df_filtrado)}")

        try:
            login = df_filtrado['login'].iloc[i].strip()
            senha = df_filtrado['senha_dist'].iloc[i]
            uc_desejada = df_filtrado['codigo'].iloc[i].zfill(12)
            id_distribuidora = int(df_filtrado['dist'].iloc[i])

            distribuidoras_map = {
                11: {'nome': 'COELBA', 'canal': 'AGC', 'regiao': 'NE', 'usuario_api': 'WSO2_CONEXAO', 'base_url': 'apineprd'},
                42: {'nome': 'COSERN', 'canal': 'AGR', 'regiao': 'NE', 'usuario_api': 'WSO2_CONEXAO', 'base_url': 'apineprd'},
                43: {'nome': 'CELP',   'canal': 'AGP', 'regiao': 'NE', 'usuario_api': 'WSO2_CONEXAO', 'base_url': 'apineprd'},
                52: {'nome': 'ELEKTRO', 'canal': 'AGE', 'regiao': 'SE', 'usuario_api': 'AGENEOELK', 'base_url': 'apiseprd'}
            }

            if id_distribuidora not in distribuidoras_map:
                continue

            distribuidora = distribuidoras_map[id_distribuidora]['nome']
            canal = distribuidoras_map[id_distribuidora]['canal']
            regiao = distribuidoras_map[id_distribuidora]['regiao']
            usuario_api = distribuidoras_map[id_distribuidora]['usuario_api']
            base_url = distribuidoras_map[id_distribuidora]['base_url']

            # Lógica de login
            precisa_logar = False
            if i == 0:
                precisa_logar = True
            elif df_filtrado['login'].iloc[i] != df_filtrado['login'].iloc[i-1]:
                precisa_logar = True
            elif not verificar_token_storage(navegador, id_distribuidora):
                precisa_logar = True

            if precisa_logar:
                navegador.get("https://agenciavirtual.neoenergia.com/#/login")
                time.sleep(3)
                
                # Clicar no botão LOGIN
                login_btn_found = False
                for elem in navegador.find_elements(By.TAG_NAME, 'button'):
                    if 'LOGIN' in elem.text.upper(): 
                        navegador.execute_script("arguments[0].click();", elem)
                        login_btn_found = True
                        break
                
                if not login_btn_found:
                    for elem in navegador.find_elements(By.XPATH, "//button | //a | //input[@type='button']"):
                         if 'LOGIN' in elem.get_attribute('innerHTML').upper() or 'LOGIN' in elem.get_attribute('value', '').upper(): 
                             navegador.execute_script("arguments[0].click();", elem)
                             login_btn_found = True
                             break
                
                time.sleep(2)
                
                # Preencher campos de login
                try:
                    campo_user = WebDriverWait(navegador, 10).until(EC.presence_of_element_located((By.ID, 'userId')))
                    campo_user.clear()
                    campo_user.send_keys(login)
                    
                    campo_senha = navegador.find_element(By.ID, 'password')
                    campo_senha.clear()
                    campo_senha.send_keys(senha)
                except Exception as e:
                    for j in range(i, len(df_filtrado)):
                        if df_filtrado['login'].iloc[j] == login: 
                            ucs_cadastro_invalido.append(df_filtrado['codigo'].iloc[j].zfill(12))
                        else: 
                            break
                    continue
                
                time.sleep(1)
                
                # Clicar no botão ENTRAR
                entrar_btn_found = False
                for elem in navegador.find_elements(By.TAG_NAME, 'button'):
                    if 'ENTRAR' in elem.text.upper(): 
                        navegador.execute_script("arguments[0].click();", elem)
                        entrar_btn_found = True
                        break
                
                if not entrar_btn_found:
                    for elem in navegador.find_elements(By.XPATH, "//button | //input[@type='submit']"):
                        if 'ENTRAR' in elem.get_attribute('innerHTML').upper() or 'ENTRAR' in elem.get_attribute('value', '').upper(): 
                            navegador.execute_script("arguments[0].click();", elem)
                            entrar_btn_found = True
                            break
                
                time.sleep(10)
                
                # Verificar se precisa trocar senha
                try:
                    aviso = WebDriverWait(navegador, 3).until(EC.presence_of_element_located((By.ID, 'swal2-html-container'))).text
                    if 'troca da sua senha' in aviso.lower():
                        for j in range(i, len(df_filtrado)):
                            if df_filtrado['login'].iloc[j] == login: 
                                ucs_ativar_cadastro.append(df_filtrado['codigo'].iloc[j].zfill(12))
                            else: 
                                break
                        continue
                except: 
                    pass
                
                # Verificar credenciais inválidas
                credenciais_invalidas = False
                try:
                    error_msgs = navegador.find_elements(By.CLASS_NAME, 'm-0')
                    for msg in error_msgs:
                        if 'CPF/CNPJ ou senha inválidos' in msg.text:
                            credenciais_invalidas = True
                            for j in range(i, len(df_filtrado)):
                                if df_filtrado['login'].iloc[j] == login: 
                                    ucs_cadastro_invalido.append(df_filtrado['codigo'].iloc[j].zfill(12))
                                else: 
                                    break
                            break
                except: 
                    pass
                
                if credenciais_invalidas: 
                    continue
                
                time.sleep(3)

            # Obter token
            token = None
            try:
                if id_distribuidora == 52:
                    token_raw = navegador.execute_script("return window.localStorage.getItem('tokenNeSe');")
                    if token_raw:
                        try: 
                            tokens = json.loads(token_raw)
                            token = tokens['se']
                        except: 
                            token = token_raw
                else:
                    token = navegador.execute_script("return window.localStorage.getItem('access_token') || window.localStorage.getItem('token');")
                
                if not token:
                    ucs_erro_sistema.append(uc_desejada)
                    continue
                    
            except Exception as e:
                ucs_erro_sistema.append(uc_desejada)
                continue

            headers = {
                'Authorization': f'Bearer {token}', 
                'Content-Type': 'application/json',
                'Accept': 'application/json', 
                'User-Agent': 'Mozilla/5.0'
            }
            time.sleep(1)
            
            # Lógica específica para cada distribuidora
            if id_distribuidora == 52:
                # ELEKTRO
                uc_info = {'uc': uc_desejada}
                
                url_protocolo = "https://apiseprd.neoenergia.com/protocolo/1.1.0/obterProtocolo"
                params_protocolo = {
                    "distribuidora": "ELEKTRO",
                    "canalSolicitante": "AGE",
                    "usuario": "AGENEOELK",
                    "documento": limpar_documento(login),
                    "recaptchaAnl": "false",
                    "regiao": "SE"
                }

                try:
                    time.sleep(1)
                    res_protocolo = fazer_requisicao_com_retry(url_protocolo, headers=headers, params=params_protocolo, method='GET')
                    
                    if not res_protocolo or res_protocolo.status_code != 200:
                        ucs_erro_sistema.append(uc_desejada)
                        ucs_erro_busca.append(uc_desejada)
                        continue
                    
                    protocolo_data = res_protocolo.json()
                    protocolo = protocolo_data.get('protocoloSalesforceStr')
                    
                    if not protocolo:
                        ucs_retidas.append(uc_desejada)
                        continue
                    
                except Exception as e:
                    ucs_retidas.append(uc_desejada)
                    continue

                url_faturas = "https://apiseprd.neoenergia.com/multilogin/2.0.0/servicos/faturas/ucs/faturas"
                params_faturas = {
                    "codigo": uc_desejada,
                    "documento": limpar_documento(login),
                    "canalSolicitante": "AGE",
                    "usuario": "AGENEOELK",
                    "protocolo": protocolo,
                    "distribuidora": "ELEKTRO",
                    "regiao": "SE",
                    "tipoPerfil": "1"
                }

                try:
                    time.sleep(1)
                    res_faturas = fazer_requisicao_com_retry(url_faturas, headers=headers, params=params_faturas, method='GET')
                    
                    if not res_faturas or res_faturas.status_code != 200:
                        ucs_erro_sistema.append(uc_desejada)
                        ucs_erro_busca.append(uc_desejada)
                        continue
                    
                    faturas_data = res_faturas.json()
                    if 'entregaFaturas' in faturas_data:
                        faturas = faturas_data['entregaFaturas'][0].get('faturas', [])
                    elif 'faturas' in faturas_data:
                        faturas = faturas_data['faturas']
                    else:
                        ucs_retidas.append(uc_desejada)
                        continue
                    
                except Exception as e:
                    ucs_retidas.append(uc_desejada)
                    continue

            else:
                # Demais distribuidoras
                login_limpo = limpar_documento(login)
                url_ucs = f'https://{base_url}.neoenergia.com/imoveis/1.1.0/clientes/{login_limpo}/ucs'
                
                params_ucs = {
                    'documento': login_limpo,
                    'canalSolicitante': canal,
                    'distribuidora': distribuidora,
                    'usuario': usuario_api,
                    'indMaisUcs': 'X',
                    'protocolo': '123',
                    'opcaoSSOS': 'S',
                    'tipoPerfil': '1'
                }

                try:
                    time.sleep(1)
                    res_ucs = fazer_requisicao_com_retry(url_ucs, headers=headers, params=params_ucs, method='GET')
                    
                    if not res_ucs or res_ucs.status_code != 200:
                        ucs_erro_sistema.append(uc_desejada)
                        ucs_erro_busca.append(uc_desejada)
                        continue
                    
                    ucs_data = res_ucs.json()
                    ucs = ucs_data.get('listaUnidadesConsumidoras') or ucs_data.get('ucs') or []
                    
                    uc_info = next((uc for uc in ucs if uc['uc'].endswith(uc_desejada[-10:])), None)
                    if not uc_info:
                        ucs_retidas.append(uc_desejada)
                        continue
                    
                except Exception as e:
                    ucs_retidas.append(uc_desejada)
                    continue

                url_protocolo = f'https://{base_url}.neoenergia.com/protocolo/1.1.0/obterProtocolo'
                params_protocolo = {
                    'distribuidora': distribuidora[:4],
                    'canalSolicitante': canal,
                    'documento': login_limpo,
                    'codCliente': uc_info['uc'],
                    'recaptchaAnl': 'false',
                    'regiao': regiao
                }

                try:
                    time.sleep(1)
                    res_protocolo = fazer_requisicao_com_retry(url_protocolo, headers=headers, params=params_protocolo, method='GET')
                    
                    if not res_protocolo or res_protocolo.status_code != 200:
                        ucs_erro_sistema.append(uc_info['uc'])
                        ucs_erro_busca.append(uc_info['uc'])
                        continue
                    
                    protocolo_data = res_protocolo.json()
                    protocolo = (protocolo_data.get('protocolo') or 
                               protocolo_data.get('protocoloSalesforceStr') or 
                               protocolo_data.get('protocoloSalesforce') or 
                               protocolo_data.get('protocoloLegadoStr') or 
                               protocolo_data.get('protocoloLegado'))
                    
                    if not protocolo:
                        ucs_retidas.append(uc_info['uc'])
                        continue
                    
                except Exception as e:
                    ucs_retidas.append(uc_info['uc'])
                    continue

                url_faturas = f'https://{base_url}.neoenergia.com/multilogin/2.0.0/servicos/faturas/ucs/faturas'
                params_faturas = {
                    'codigo': uc_info['uc'],
                    'documento': login_limpo,
                    'canalSolicitante': canal,
                    'usuario': usuario_api,
                    'protocolo': protocolo,
                    'byPassActiv': 'X',
                    'documentoSolicitante': login_limpo,
                    'documentoCliente': login_limpo,
                    'distribuidora': distribuidora,
                    'tipoPerfil': '1'
                }

                try:
                    time.sleep(1)
                    res_faturas = fazer_requisicao_com_retry(url_faturas, headers=headers, params=params_faturas, method='GET')
                    
                    if not res_faturas or res_faturas.status_code != 200:
                        ucs_erro_sistema.append(uc_info['uc'])
                        ucs_erro_busca.append(uc_info['uc'])
                        continue
                    
                    faturas_data = res_faturas.json()
                    faturas = faturas_data.get("faturas", [])
                    
                except Exception as e:
                    ucs_retidas.append(uc_info['uc'])
                    continue

            # Processar faturas
            if not faturas:
                ucs_sem_fatura.append(uc_info.get('uc', uc_desejada))
                continue

            try:
                if id_distribuidora == 52:
                    f_mais_recente = sorted(faturas, key=lambda f: f.get("dataCompetencia", ""), reverse=True)[0]
                    if f_mais_recente.get("dataCompetencia", "")[:7].replace('-', '/') <= mes_atraso.replace('/', '-'):
                        ucs_inativas.append(uc_info['uc'])
                else:
                    f_mais_recente = sorted(faturas, key=lambda f: f.get("mesReferencia", ""), reverse=True)[0]
                    if f_mais_recente.get("mesReferencia") <= mes_atraso:
                        ucs_inativas.append(uc_info['uc'])
            except IndexError:
                ucs_sem_fatura.append(uc_info.get('uc', uc_desejada))
                continue

            st.write(f"🔍 Busca {i+1} de {len(df_filtrado)}")
            st.write(f"✅ Protocolo: {protocolo}")
            st.write(f"✅ {len(faturas)} faturas encontradas")
            
            if id_distribuidora == 52:
                st.write(f"🧾 Mais recente: {f_mais_recente.get('dataCompetencia')}")
            else:
                st.write(f"🧾 Mais recente: {f_mais_recente.get('mesReferencia')}")

            # Baixar faturas dos meses desejados
            faturas_baixadas_neste_mes = 0
            meses_lista = [mes.strip() for mes in meses_desejados.split(",")]
            
            for mes_desejada in meses_lista:
                fatura_desejada = None
                
                if id_distribuidora == 52:
                    mes_desejada_formatada = mes_desejada.replace('/', '-')
                    fatura_desejada = next((f for f in faturas if f.get('dataCompetencia', '').startswith(mes_desejada_formatada)), None)
                else:
                    fatura_desejada = next((f for f in faturas if f.get('mesReferencia') == mes_desejada), None)
                
                if not fatura_desejada:
                    st.write(f"⚠️ Fatura do mês {mes_desejada} não encontrada.")
                    if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                        ucs_retidas.append(uc_info.get('uc', uc_desejada))
                    continue

                numero_fatura = fatura_desejada.get('numeroFatura')
                if not numero_fatura:
                    if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                        ucs_retidas.append(uc_info.get('uc', uc_desejada))
                    continue

                # Download do PDF
                url_pdf = f"https://{base_url}.neoenergia.com/multilogin/2.0.0/servicos/faturas/{numero_fatura}/pdf"
                
                if id_distribuidora == 52:
                    params_pdf = {
                        "codigo": uc_info.get('uc', uc_desejada),
                        "protocolo": protocolo,
                        "tipificacao": fatura_desejada.get('tipificacao', "1031607"),
                        "usuario": usuario_api,
                        "canalSolicitante": canal,
                        "distribuidora": distribuidora,
                        "regiao": regiao,
                        "tipoPerfil": "1",
                        "documento": limpar_documento(login),
                    }
                else:
                    params_pdf = {
                        "codigo": uc_info.get('uc', uc_desejada),
                        "protocolo": protocolo,
                        "tipificacao": fatura_desejada.get('tipificacao', "1031607"),
                        "usuario": usuario_api,
                        "canalSolicitante": canal,
                        "distribuidora": distribuidora,
                        "regiao": regiao,
                        "tipoPerfil": "1",
                        "documento": limpar_documento(login),
                        "documentoSolicitante": limpar_documento(login),
                        "documentoCliente": limpar_documento(login),
                        "byPassActiv": "X",
                        "motivo": "2"
                    }

                try:
                    time.sleep(1)
                    
                    res_pdf = fazer_requisicao_com_retry(
                        url_pdf, 
                        headers=headers, 
                        params=params_pdf, 
                        method='GET',
                        skip_retry_errors=ERRORS_SEM_RETRY
                    )
                    
                    if not res_pdf:
                        if uc_info.get('uc', uc_desejada) not in ucs_erro_sistema:
                            ucs_erro_sistema.append(uc_info.get('uc', uc_desejada))
                        if uc_info.get('uc', uc_desejada) not in ucs_erro_busca:
                            ucs_erro_busca.append(uc_info.get('uc', uc_desejada))
                        continue
                    
                    if res_pdf.status_code != 200:
                        if "Fatura indisponível no canal digital" in res_pdf.text:
                            if uc_info.get('uc', uc_desejada) not in ucs_fatura_indisponivel:
                                ucs_fatura_indisponivel.append(uc_info.get('uc', uc_desejada))
                        elif "falha ao checar relação 'documento' - 'uc'" in res_pdf.text:
                            if uc_info.get('uc', uc_desejada) not in ucs_cadastro_invalido:
                                ucs_cadastro_invalido.append(uc_info.get('uc', uc_desejada))
                        else:
                            if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                                ucs_retidas.append(uc_info.get('uc', uc_desejada))
                        continue

                    # Processar resposta do PDF
                    content_type = res_pdf.headers.get('Content-Type', '')
                    mes_ref = mes_desejada.replace('/', '-')
                    dir_base = os.path.join(os.getcwd(), diretorio_download, mes_ref)
                    os.makedirs(dir_base, exist_ok=True)
                    
                    nome_distribuidora = distribuidora.upper()
                    codigo_uc = uc_info.get('uc', uc_desejada)
                    nome_arquivo = f"{nome_distribuidora}_{codigo_uc}_{mes_ref}.pdf"
                    caminho_completo = os.path.join(dir_base, nome_arquivo)

                    if 'application/json' in content_type:
                        data_json = res_pdf.json()
                        base64_pdf = data_json.get("fileData") or data_json.get("faturaBase64")
                        if base64_pdf:
                            with open(caminho_completo, "wb") as f:
                                f.write(base64.b64decode(base64_pdf))
                            faturas_baixadas_neste_mes += 1
                            st.success(f"✅ PDF baixado: {nome_arquivo}")
                        else:
                            if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                                ucs_retidas.append(uc_info.get('uc', uc_desejada))
                    
                    elif 'application/pdf' in content_type:
                        with open(caminho_completo, "wb") as f:
                            f.write(res_pdf.content)
                        faturas_baixadas_neste_mes += 1
                        st.success(f"✅ PDF baixado: {nome_arquivo}")
                    
                    else:
                        if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                            ucs_retidas.append(uc_info.get('uc', uc_desejada))
                            
                except Exception as e:
                    if uc_info.get('uc', uc_desejada) not in ucs_retidas:
                        ucs_retidas.append(uc_info.get('uc', uc_desejada))

            # Contabilizar sucesso
            if faturas_baixadas_neste_mes > 0:
                if uc_info.get('uc', uc_desejada) not in ucs_sucesso:
                    ucs_sucesso.append(uc_info.get('uc', uc_desejada))

            # Tempo da UC
            fim_uc = time.perf_counter()
            tempo_uc = fim_uc - inicio_uc
            tempos_ucs.append((df_filtrado['codigo'].iloc[i], round(tempo_uc, 2)))
            st.write(f"⏱️ Tempo desta UC: {tempo_uc:.2f} segundos")

        except Exception as e:
            if df_filtrado['codigo'].iloc[i] not in ucs_retidas:
                ucs_retidas.append(df_filtrado['codigo'].iloc[i])

    # Finalizar navegador
    if navegador:
        navegador.quit()
    
    tempo_total_fim = time.perf_counter()
    tempo_total = tempo_total_fim - tempo_total_inicio

    # Relatório final
    ucs_sucesso_set = set(ucs_sucesso)
    ucs_retidas_set = set(ucs_retidas) - ucs_sucesso_set
    ucs_fatura_indisponivel_set = set(ucs_fatura_indisponivel) - ucs_sucesso_set
    ucs_erro_sistema_set = set(ucs_erro_sistema) - ucs_sucesso_set
    ucs_erro_busca_set = set(ucs_erro_busca) - ucs_sucesso_set
    ucs_sem_fatura_set = set(ucs_sem_fatura) - ucs_sucesso_set
    ucs_inativas_set = set(ucs_inativas) - ucs_sucesso_set
    ucs_ativar_cadastro_set = set(ucs_ativar_cadastro) - ucs_sucesso_set
    ucs_cadastro_invalido_set = set(ucs_cadastro_invalido) - ucs_sucesso_set
    
    st.write("\n🧾 === RELATÓRIO FINAL ===")
    st.write(f"📊 Total UCs: {len(df_filtrado)}")
    st.write(f"✅ Sucesso: {len(ucs_sucesso_set)}")
    st.write(f"📦 Retidas: {len(ucs_retidas_set)}")
    st.write(f"🚫 Indisponíveis: {len(ucs_fatura_indisponivel_set)}")
    st.write(f"🔴 Erros Sistema: {len(ucs_erro_sistema_set)}")
    st.write(f"❌ Erros Busca: {len(ucs_erro_busca_set)}")
    st.write(f"📭 Sem Fatura: {len(ucs_sem_fatura_set)}")
    st.write(f"⛔ Inativas: {len(ucs_inativas_set)}")
    st.write(f"🔐 Ativar Cadastro: {len(ucs_ativar_cadastro_set)}")
    st.write(f"🔑 Cred. Inválidas: {len(ucs_cadastro_invalido_set)}")
    st.write(f"\n⏲️ Tempo Total: {tempo_total:.2f} seg")
    
    resultados = {
        'ucs_processadas': len(df_filtrado),
        'ucs_sucesso': list(ucs_sucesso_set),
        'ucs_retidas': list(ucs_retidas_set),
        'ucs_fatura_indisponivel': list(ucs_fatura_indisponivel_set),
        'ucs_erro_sistema': list(ucs_erro_sistema_set),
        'ucs_erro_busca': list(ucs_erro_busca_set),
        'ucs_sem_fatura': list(ucs_sem_fatura_set),
        'ucs_inativas': list(ucs_inativas_set),
        'ucs_ativar_cadastro': list(ucs_ativar_cadastro_set),
        'ucs_cadastro_invalido': list(ucs_cadastro_invalido_set),
        'tempo_total': tempo_total,
        'tempos_ucs': tempos_ucs
    }
    
    return resultados

# ----------------------------
# Função principal
# ----------------------------
def main():
    st.sidebar.header("⚙️ Configurações do Scraper")
    
    # Configurações do usuário
    headless = st.sidebar.checkbox("Modo Headless (sem interface gráfica)", value=True)
    meses_desejados = st.sidebar.text_input("Meses desejados (separados por vírgula)", "2025/10")
    mes_atraso = st.sidebar.text_input("Mês limite para UC inativa", "2025/06")
    
    # Adicionar seção de downloads na sidebar
    st.sidebar.header("📥 Downloads")
    if st.sidebar.button("🔄 Atualizar Lista de Arquivos"):
        st.rerun()
    
    try:
        with st.spinner("🔗 Conectando ao Google Sheets..."):
            gc = autorizar_google()
        
        if not gc:
            st.error("❌ Não foi possível conectar ao Google Sheets")
            return
            
        sheet_key = "1gI3h3F1ALScglYfr7NIfAxYyV0NSVjEJvoKFarlywBY"
        sheet_name = "bd_ucs"

        spreadsheet = gc.open_by_key(sheet_key)
        sheet = spreadsheet.worksheet(sheet_name)

        dados = sheet.get_all_values()
        df = pd.DataFrame(dados[1:], columns=dados[0])

        df.columns = ['uc_id', 'cliente_id_gestor', 'distribuidora_id', 'codigo', 'login',
                        'senha_dist', 'Status', 'documento', 'Distribuidora',
                        'Status_Mes_Anterior', 'data_geracao', 'nome', 'Geradora?',
                        'Clientes', 'Estimativa', 'Status2', 'Historico_Faturas',
                        'StatusContrato', 'Senha_modificada', 'Status_TEST']

        df['Estimativa'] = pd.to_numeric(df['Estimativa'], errors='coerce').fillna(0).astype(int)

        st.subheader("🔍 Filtros de Seleção")
        
        # Filtro por Clientes
        clientes_unicos = df['Clientes'].unique().tolist()
        clientes_unicos.insert(0, "Todos os Clientes")
        
        cliente_selecionado = st.sidebar.selectbox(
            "Selecione o Cliente:",
            options=clientes_unicos,
            index=0,
            help="Selecione um cliente específico ou 'Todos os Clientes'"
        )
        
        # Aplicar filtro de cliente
        if cliente_selecionado == "Todos os Clientes":
            clientes_selecionados = clientes_unicos[1:]
        else:
            clientes_selecionados = [cliente_selecionado]
        
        col1, col2 = st.columns(2)
        with col1:
            estimativa_inicio = st.number_input("Início do intervalo da Estimativa:", 
                                                value=int(df['Estimativa'].min()))
        with col2:
            estimativa_fim = st.number_input("Fim do intervalo da Estimativa:", 
                                            value=int(df['Estimativa'].max()))

        # Filtro por código UC
        st.sidebar.subheader("🔄 Reset por Código UC")
        codigo_uc_inicio = st.sidebar.text_input(
            "Código UC para iniciar busca:",
            placeholder="Digite o código UC para começar a partir dele"
        )

        # Aplicar filtros iniciais
        df_filtrado = df.loc[
            ((df['Distribuidora'].isin(['COELBA','COSERN','NEOENERGIA PE','ELEKTRO'])) &
             (df['Status'].isin(['Acesso Ok','Sem fatura do mês de referencia','Retida'])) &
             (df['Status_TEST'] == 'A baixar') &
             (df['Estimativa'] >= estimativa_inicio) &
             (df['Estimativa'] <= estimativa_fim) &
             (df['Clientes'].isin(clientes_selecionados))),
            ['distribuidora_id','codigo', 'login', 'senha_dist']
        ].copy()

        st.sidebar.info(f"📊 UCs após filtros básicos: {len(df_filtrado)}")

        # Aplicar filtro por código UC se especificado
        if codigo_uc_inicio and codigo_uc_inicio.strip():
            codigo_uc_inicio = codigo_uc_inicio.strip()
            try:
                df_filtrado_reset = df_filtrado.reset_index(drop=True)
                indices = df_filtrado_reset.index[df_filtrado_reset['codigo'] == codigo_uc_inicio].tolist()
                
                if indices:
                    start_index = indices[0]
                    df_filtrado = df_filtrado_reset.iloc[start_index:].copy()
                    st.sidebar.success(f"✅ Busca iniciará a partir da UC: {codigo_uc_inicio}")
            except Exception as e:
                st.sidebar.error(f"❌ Erro ao processar código UC: {e}")

        # Preencher senhas vazias e ordenar
        df_filtrado["senha_dist"] = df_filtrado["senha_dist"].fillna("")

        if len(df_filtrado) > 0:
            frequencia_login = df_filtrado['login'].value_counts()
            df_filtrado = df_filtrado.copy()
            df_filtrado['frequencia_login'] = df_filtrado['login'].map(frequencia_login)
            df_filtrado = df_filtrado.sort_values(['frequencia_login', 'login'], ascending=[False, True])
            df_filtrado = df_filtrado.drop('frequencia_login', axis=1)
            df_filtrado = df_filtrado.reset_index(drop=True)

        df_filtrado.columns = ['dist','codigo','login','senha_dist']

        st.subheader("📊 Dados Filtrados para Processamento")
        
        if len(df_filtrado) > 0:
            st.dataframe(df_filtrado, use_container_width=True)
            st.success(f"✅ Total de registros para processar: {len(df_filtrado)}")
        else:
            st.error("❌ Nenhum registro encontrado para processar.")
            return

        # Botões de controle
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Iniciar Extração de Faturas", type="primary", use_container_width=True):
                if len(df_filtrado) == 0:
                    st.warning("⚠️ Nenhum registro encontrado para processar.")
                    return
                
                st.session_state.executando = True
                st.session_state.parar_execucao = False
                
                st.subheader("📈 Progresso da Extração")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with st.spinner("🔄 Executando extração de faturas..."):
                    resultados = executar_scraper(df_filtrado, progress_bar, status_text, meses_desejados, mes_atraso, headless)
                
                if resultados:
                    progress_bar.progress(1.0)
                    status_text.text("✅ Extração concluída!")
                    st.session_state.executando = False

        with col2:
            if st.button("⏹️ Parar Execução", type="secondary", use_container_width=True):
                parar_execucao()
                st.warning("⏹️ Comando para parar execução enviado.")

        # Exibir seção de downloads
        exibir_secao_downloads()

    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")

# 🚀 INICIAR APLICAÇÃO
# 🎯 SOLUÇÃO PARA RAILWAY - Usar porta do ambiente
if __name__ == "__main__":
    port = os.environ.get("PORT", "8000")
    
    print(f"🚀 INICIANDO STREAMLIT NA PORTA {port}...")
    
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", __file__,
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.serverAddress", "0.0.0.0"
    ]
    stcli.main()



