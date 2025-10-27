import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# =============================================
# HEALTH CHECK SERVER (PRIMEIRA COISA)
# =============================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/health', '/', '/_stcore/health']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Silenciar logs do health check
        pass

def start_health_server():
    """Inicia servidor de health check na porta 8080"""
    try:
        port = int(os.environ.get('HEALTH_PORT', '8080'))
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"✅ Health check server iniciado na porta {port}")
        server.serve_forever()
    except Exception as e:
        print(f"❌ Health check server falhou: {e}")

# Iniciar health check em thread separada
health_thread = threading.Thread(target=start_health_server, daemon=True)
health_thread.start()
print("🚀 Health check iniciado, iniciando Streamlit...")

# =============================================
# CONFIGURAÇÃO STREAMLIT
# =============================================

# Aguardar um pouco para o health check iniciar
time.sleep(2)

# Agora importar e configurar Streamlit
import streamlit as st

# Configurar página
st.set_page_config(
    page_title="Sistema Neoenergia",
    layout="wide",
    page_icon="🏭"
)

# =============================================
# APLICAÇÃO PRINCIPAL
# =============================================

def main():
    st.title("🏭 Sistema de Faturas Neoenergia")
    st.success("✅ Aplicação carregada com sucesso!")
    
    # Informações do sistema
    st.sidebar.header("📊 Informações do Sistema")
    st.sidebar.write(f"**Porta:** {os.environ.get('PORT', 'Não definida')}")
    st.sidebar.write(f"**Railway:** {'✅ SIM' if 'RAILWAY_ENVIRONMENT' in os.environ else '❌ NÃO'}")
    
    # Teste simples
    st.header("🧪 Teste Básico")
    
    if st.button("Testar Aplicação"):
        st.balloons()
        st.success("🎉 Aplicação funcionando perfeitamente!")
    
    # Verificar dependências
    st.header("📦 Dependências")
    
    try:
        import pandas as pd
        st.success(f"✅ pandas {pd.__version__}")
    except ImportError:
        st.error("❌ pandas não instalado")
    
    try:
        import gspread
        st.success(f"✅ gspread {gspread.__version__}")
    except ImportError:
        st.error("❌ gspread não instalado")
    
    try:
        import selenium
        st.success(f"✅ selenium {selenium.__version__}")
    except ImportError:
        st.error("❌ selenium não instalado")
    
    # Verificar variáveis de ambiente Google
    st.header("🔐 Variáveis de Ambiente")
    
    google_vars = ['GCP_PROJECT_ID', 'GCP_CLIENT_EMAIL']
    for var in google_vars:
        if var in os.environ:
            value = os.environ[var]
            display_value = value[:20] + "..." if len(value) > 20 else value
            st.success(f"✅ {var}: {display_value}")
        else:
            st.error(f"❌ {var}: Não definida")

if __name__ == "__main__":
    main()
