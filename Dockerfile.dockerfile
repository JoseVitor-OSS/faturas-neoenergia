FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Dar permissão de execução ao script
RUN chmod +x start.sh

EXPOSE 8000

# Usar o script shell
CMD ["./start.sh"]
