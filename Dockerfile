# Use a imagem base do Python
FROM python:3.11

# Configuração do diretório de trabalho
WORKDIR /app

# Copie os arquivos necessários para o contêiner
COPY . /app

# Instalação das dependências
RUN pip install -r requirements.txt

# Expõe a porta em que sua aplicação Flask está sendo executada
EXPOSE 5000

# Comando para iniciar a aplicação Flask
CMD ["python3", "app/mqtt_data_reader.py"]
