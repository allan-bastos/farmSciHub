#!/bin/bash

# Nome da imagem
IMAGE_NAME="data-reader"

# Nome do container
CONTAINER_NAME="data-reader"

# Parando o serviço
#sudo systemctl stop crud_dispositivo.service

# Parando e removendo o container existente
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

# Removendo a imagem anterior (se existir)
docker rmi $IMAGE_NAME

# Construindo a nova imagem
docker build -t $IMAGE_NAME .

# Criando um novo container com a imagem atualizada
docker run -d -p 8002:8002 --name $CONTAINER_NAME $IMAGE_NAME

# Iniciando o serviço
#sudo systemctl start crud_dispositivo.service
