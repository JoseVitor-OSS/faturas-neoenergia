import os
import sys
import streamlit as st
import logging
from datetime import datetime

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()

# Log inicial
log_message("🚀 INICIANDO APLICAÇÃO STREAMLIT")
log_message(f"Python version: {sys.version}")
log_message(f"Working directory: {os.getcwd()}")
log_message(f"Files in directory: {os.listdir('.')}")

try:
    # Tentar importar dependências
    log_message("📦 IMPORTANDO DEPENDÊNCIAS...")
    
    import pandas as pd
    log_message("✅ pandas importado")
    
    import gspread
    log_message("✅ gspread importado")
    
    from google.oauth2.service_account import Credentials
    log_message("✅ google-auth importado")
    
    import selenium
    log_message("✅ selenium importado")
    
    log_message("✅ TODAS AS DEPENDÊNCIAS IMPORTADAS COM SUCESSO")
    
except ImportError as e:
    log_message(f"❌ ERRO DE IMPORT: {e}")
    sys.exit(1)

# Configurar página Streamlit
try:
    log_message("⚙️ CONFIGURANDO PÁGINA STREAMLIT...")
    st.set_page_config(
        page_title="Debug App",
        layout="wide",
        page_icon="🐛"
    )
    log_message("✅ Página Streamlit configurada")
except Exception as e:
    log_message(f"❌ ERRO NA CONFIGURAÇÃO: {e}")

# Função principal
def main():
    log_message("🎯 INICIANDO FUNÇÃO MAIN()")
    
    try:
        st.title("🐛 Debug Application - Railway")
        st.markdown("---")
        
        # Seção 1: Informações do Sistema
        st.header("📊 Informações do Sistema")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Python")
            st.code(f"Version: {sys.version}")
            st.code(f"Executable: {sys.executable}")
        
        with col2:
            st.subheader("Diretório")
            st.code(f"Current: {os.getcwd()}")
            files = os.listdir('.')
            st.code(f"Files: {len(files)}")
            for f in files:
                st.write(f" - {f}")
        
        with col3:
            st.subheader("Variáveis de Ambiente")
            env_vars = [
                "PORT", "RAILWAY_ENVIRONMENT", "RAILWAY_STATIC_URL",
                "GCP_PROJECT_ID", "GCP_CLIENT_EMAIL"
            ]
            for var in env_vars:
                value = os.environ.get(var, "NÃO DEFINIDA")
                st.write(f"**{var}**: `{value}`")
        
        # Seção 2: Teste de Dependências
        st.header("🧪 Teste de Dependências")
        
        dependencies = [
            ("streamlit", st.__version__),
            ("pandas", pd.__version__),
            ("gspread", gspread.__version__),
            ("selenium", selenium.__version__),
        ]
        
        for dep, version in dependencies:
            st.success(f"✅ {dep}: {version}")
        
        # Seção 3: Teste de Google Sheets
        st.header("🔗 Teste de Google Sheets")
        
        if st.button("Testar Conexão Google Sheets"):
            try:
                log_message("🔗 TESTANDO CONEXÃO GOOGLE SHEETS...")
                
                # Verificar variáveis de ambiente
                required_vars = ['GCP_PROJECT_ID', 'GCP_PRIVATE_KEY', 'GCP_CLIENT_EMAIL']
                missing_vars = [var for var in required_vars if var not in os.environ]
                
                if missing_vars:
                    st.error(f"❌ Variáveis faltando: {missing_vars}")
                    log_message(f"VARIÁVEIS FALTANDO: {missing_vars}")
                else:
                    st.success("✅ Variáveis de ambiente presentes")
                    
                    # Tentar autenticar
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
                    st.success("✅ Autenticação Google Sheets bem-sucedida!")
                    log_message("✅ GOOGLE SHEETS: Autenticação OK")
                    
                    # Tentar acessar planilha
                    try:
                        sheet_key = "1gI3h3F1ALScglYfr7NIfAxYyV0NSVjEJvoKFarlywBY"
                        spreadsheet = gc.open_by_key(sheet_key)
                        sheet = spreadsheet.worksheet("bd_ucs")
                        dados = sheet.get_all_values()
                        
                        st.success(f"✅ Planilha acessada: {len(dados)} linhas")
                        log_message(f"✅ PLANILHA: {len(dados)} linhas carregadas")
                        
                        # Mostrar preview
                        if len(dados) > 1:
                            df = pd.DataFrame(dados[1:], columns=dados[0])
                            st.dataframe(df.head(3))
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao acessar planilha: {e}")
                        log_message(f"❌ ERRO PLANILHA: {e}")
                        
            except Exception as e:
                st.error(f"❌ Erro na autenticação: {e}")
                log_message(f"❌ ERRO AUTENTICAÇÃO: {e}")
        
        # Seção 4: Teste de Selenium
        st.header("🌐 Teste de Selenium")
        
        if st.button("Testar Selenium"):
            try:
                log_message("🌐 TESTANDO SELENIUM...")
                
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                
                # Verificar se Chrome está disponível
                import subprocess
                result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
                st.write(f"Chrome path: {result.stdout}")
                
                result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
                st.write(f"ChromeDriver path: {result.stdout}")
                
                # Tentar iniciar navegador
                driver = webdriver.Chrome(options=chrome_options)
                st.success("✅ Navegador Chrome iniciado com sucesso!")
                
                # Testar navegação
                driver.get("https://httpbin.org/ip")
                st.success(f"✅ Página carregada: {driver.title}")
                
                driver.quit()
                st.success("✅ Navegador fechado com sucesso!")
                log_message("✅ SELENIUM: Teste completo com sucesso")
                
            except Exception as e:
                st.error(f"❌ Erro no Selenium: {e}")
                log_message(f"❌ ERRO SELENIUM: {e}")
        
        # Seção 5: Health Check
        st.header("❤️ Health Check")
        st.success("✅ Aplicação está respondendo!")
        
        log_message("✅ MAIN() EXECUTADA COM SUCESSO")
        
    except Exception as e:
        log_message(f"❌ ERRO CRÍTICO NO MAIN(): {e}")
        st.error(f"Erro crítico: {e}")
        import traceback
        st.code(traceback.format_exc())

# Executar aplicação
if __name__ == "__main__":
    log_message("🎬 INICIANDO APLICAÇÃO...")
    try:
        main()
        log_message("🏁 APLICAÇÃO FINALIZADA COM SUCESSO")
    except Exception as e:
        log_message(f"💥 ERRO FATAL: {e}")
        import traceback
        log_message(traceback.format_exc())
