# Use a imagem base do Python
FROM python:3.11

# Configuração do diretório de trabalho
WORKDIR /data_reader

# Copie os arquivos necessários para o contêiner
COPY . /data_reader

# Instalação das dependências
RUN pip install -r requirements.txt

# Expõe a porta em que sua aplicação Flask está sendo executada
EXPOSE 8002

# Comando para iniciar a aplicação Flask
CMD ["python3", "data_reader.py"]
