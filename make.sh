#!/bin/bash

# Contenido del Dockerfile
cat > Dockerfile <<EOF
# Utilizamos la imagen oficial de Python
FROM python:3.9-slim

# Establecemos el directorio de trabajo en /app
WORKDIR /app

# Copiamos los archivos de la aplicación al contenedor
COPY . .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutamos el script cuando se inicie el contenedor
CMD ["python", "data_query.py"]
EOF

# Contenido del docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3'
services:
  data_query:
    build: .
    volumes:
      - ./data:/app/data  # Montamos un volumen para persistir los datos guardados
    environment:
      - ENDPOINT_URL=http://ejemplo.com/api/data  # Reemplaza esto con la URL real del endpoint
EOF

# Contenido del requirements.txt
echo "requests==2.26.0" > requirements.txt

echo "Archivos generados con éxito: Dockerfile, docker-compose.yml, requirements.txt"
