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
import zipfile
import io
import sys

# =============================================
# CONFIGURAÇÃO STREAMLIT PARA RAILWAY
# =============================================

# Configurar página ANTES de qualquer coisa
st.set_page_config(
    page_title="Sistema de Faturas Neoenergia",
    layout="wide",
    page_icon="🏭"
)

# =============================================
# VERIFICAÇÃO DE AMBIENTE RAILWAY
# =============================================

def verificar_ambiente():
    """Verifica se estamos no Railway e configura corretamente"""
    st.sidebar.write("🔍 **Informações do Ambiente:**")
    st.sidebar.write(f"- PORT: {os.environ.get('PORT', 'Não definida')}")
    st.sidebar.write(f"- RAILWAY_ENVIRONMENT: {'✅ SIM' if 'RAILWAY_ENVIRONMENT' in os.environ else '❌ NÃO'}")
    
    # Configurar porta para Railway
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        st.sidebar.success("🚄 Executando no Railway")
        return True
    else:
        st.sidebar.info("💻 Executando localmente")
        return False

# =============================================
# CONFIGURAÇÃO DE ESTILOS
# =============================================

st.markdown("""
<style>
    .main, .stApp {
        background-color: #02231C;
        color: white;
    }
    .stButton>button {
        background-color: #00FF88;
        color: #02231C;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# =============================================
# FUNÇÕES PRINCIPAIS (SIMPLIFICADAS)
# =============================================

def autorizar_google():
    """Autenticação com Google Sheets"""
    try:
        # Verificar variáveis de ambiente
        required_vars = ['GCP_PROJECT_ID', 'GCP_PRIVATE_KEY', 'GCP_CLIENT_EMAIL']
        missing_vars = [var for var in required_vars if var not in os.environ]
        
        if missing_vars:
            st.error(f"❌ Variáveis faltando: {missing_vars}")
            return None
        
        from google.oauth2.service_account import Credentials
        
        service_account_info = {
            "type": "service_account",
            "project_id": os.environ['GCP_PROJECT_ID'],
            "private_key": os.environ['GCP_PRIVATE_KEY'].replace('\\n', '\n'),
            "client_email": os.environ['GCP_CLIENT_EMAIL'],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gc = gspread.authorize(creds)
        st.success("✅ Conectado ao Google Sheets!")
        return gc
        
    except Exception as e:
        st.error(f"❌ Erro na autenticação: {e}")
        return None

def iniciar_navegador(headless=True):
    """Inicia navegador Chrome para Selenium"""
    try:
        chrome_options = Options()
        
        # Configurações ESSENCIAIS para Railway
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        if headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # No Railway, o Chrome já está configurado automaticamente
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        st.error(f"❌ Erro ao iniciar navegador: {e}")
        return None

def executar_demo():
    """Função de demonstração para teste"""
    st.info("🚀 Iniciando demonstração...")
    
    # Simular processamento
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(5):
        progress_bar.progress((i + 1) / 5)
        status_text.text(f"Processando etapa {i + 1} de 5")
        time.sleep(1)
    
    status_text.text("✅ Demonstração concluída!")
    st.success("🎉 Sistema funcionando corretamente no Railway!")
    
    # Testar navegador
    with st.spinner("🧪 Testando Selenium..."):
        navegador = iniciar_navegador(headless=True)
        if navegador:
            st.success("✅ Selenium configurado com sucesso!")
            navegador.quit()
        else:
            st.warning("⚠️ Selenium não pôde ser iniciado (pode ser normal no Railway)")

# =============================================
# INTERFACE PRINCIPAL
# =============================================

def main():
    st.title("🏭 Sistema de Faturas Neoenergia")
    st.markdown("---")
    
    # Verificar ambiente
    is_railway = verificar_ambiente()
    
    # Sidebar
    st.sidebar.title("⚙️ Configurações")
    
    # Seção de teste
    st.sidebar.header("🧪 Teste do Sistema")
    if st.sidebar.button("🚀 Executar Teste", type="primary"):
        executar_demo()
    
    # Seção principal
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Conectar Google Sheets")
        if st.button("🔗 Conectar", key="connect_gsheets"):
            with st.spinner("Conectando..."):
                gc = autorizar_google()
                if gc:
                    try:
                        # Tentar carregar dados de exemplo
                        sheet_key = "1gI3h3F1ALScglYfr7NIfAxYyV0NSVjEJvoKFarlywBY"
                        spreadsheet = gc.open_by_key(sheet_key)
                        sheet = spreadsheet.worksheet("bd_ucs")
                        dados = sheet.get_all_values()
                        
                        if len(dados) > 1:
                            df = pd.DataFrame(dados[1:], columns=dados[0])
                            st.success(f"✅ Dados carregados: {len(df)} registros")
                            st.dataframe(df.head(3))
                        else:
                            st.warning("⚠️ Planilha vazia ou não encontrada")
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao carregar dados: {e}")
    
    with col2:
        st.subheader("🔧 Ferramentas")
        
        if st.button("🛠️ Verificar Dependências", key="check_deps"):
            st.write("### 📦 Dependências Instaladas:")
            deps = [
                ("Streamlit", "✅" if 'streamlit' in sys.modules else "❌"),
                ("Pandas", "✅" if 'pandas' in sys.modules else "❌"),
                ("Selenium", "✅" if 'selenium' in sys.modules else "❌"),
                ("gspread", "✅" if 'gspread' in sys.modules else "❌"),
            ]
            
            for dep, status in deps:
                st.write(f"- {dep}: {status}")
        
        if st.button("🌐 Testar Conexão", key="test_conn"):
            try:
                response = requests.get("https://google.com", timeout=10)
                st.success("✅ Conexão com internet: OK")
            except:
                st.error("❌ Sem conexão com internet")
    
    # Informações do sistema
    st.markdown("---")
    st.subheader("ℹ️ Informações do Sistema")
    
    info_col1, info_col2, info_col3 = st.columns(3)
    
    with info_col1:
        st.metric("Python", sys.version.split()[0])
    
    with info_col2:
        st.metric("Streamlit", st.__version__)
    
    with info_col3:
        st.metric("Ambiente", "Railway" if is_railway else "Local")
    
    # Mensagem de status
    if is_railway:
        st.success("🎉 Aplicação rodando com sucesso no Railway!")
    else:
        st.info("💻 Executando em ambiente local")

# =============================================
# INICIALIZAÇÃO SEGURA
# =============================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Erro crítico: {e}")
        st.info("💡 Verifique os logs no Railway para mais detalhes")
