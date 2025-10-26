import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# Configuração básica
st.set_page_config(page_title="Sistema de Faturas Neoenergia", layout="wide")
st.title("🏭 Sistema de Extração de Faturas Neoenergia")

def autorizar_google():
    """Autenticação simples"""
    try:
        st.write("🔍 Tentando autenticar...")
        
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            st.write("✅ Secrets encontrados")
            secrets = st.secrets['gcp_service_account']
            
            creds = Credentials.from_service_account_info(
                secrets,
                scopes=["https://www.googleapis.com/auth/spreadsheets", 
                       "https://www.googleapis.com/auth/drive"]
            )
            gc = gspread.authorize(creds)
            st.success("✅ Conectado ao Google Sheets!")
            return gc
        else:
            st.error("❌ Secrets não encontrados")
            return None
            
    except Exception as e:
        st.error(f"❌ Erro na autenticação: {e}")
        return None

def main():
    st.write("🚀 Iniciando aplicação...")
    
    # Sidebar básica
    st.sidebar.header("⚙️ Configurações")
    headless = st.sidebar.checkbox("Modo Headless", value=False)
    
    try:
        # Tentar conectar ao Google Sheets
        with st.spinner("Conectando ao Google Sheets..."):
            gc = autorizar_google()
        
        if not gc:
            st.stop()
            
        # Carregar dados
        st.write("📊 Carregando dados...")
        sheet_key = "1gI3h3F1ALScglYfr7NIfAxYyV0NSVjEJvoKFarlywBY"
        spreadsheet = gc.open_by_key(sheet_key)
        sheet = spreadsheet.worksheet("bd_ucs")
        
        dados = sheet.get_all_values()
        df = pd.DataFrame(dados[1:], columns=dados[0])
        
        st.success(f"✅ {len(df)} registros carregados!")
        
        # Mostrar dados básicos
        st.subheader("📋 Dados Carregados")
        st.dataframe(df.head(10))
        
        # Mostrar estatísticas
        st.subheader("📈 Estatísticas")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total UCs", len(df))
        with col2:
            st.metric("Distribuidoras", df['Distribuidora'].nunique())
        with col3:
            st.metric("Clientes", df['Clientes'].nunique())
            
        # Botão simples
        if st.button("🚀 Testar Scraper"):
            st.info("Scraper funcionaria aqui...")
        
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        st.stop()

if __name__ == "__main__":
    main()
