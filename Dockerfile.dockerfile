FROM python:3.11-slim

# Instalar Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Copiar código
WORKDIR /app
COPY . .

# Instalar dependências Python
RUN pip install -r requirements.txt

# Expor porta
EXPOSE 8000

# Comando para rodar
CMD streamlit run app.py --server.port=8000 --server.address=0.0.0.0
