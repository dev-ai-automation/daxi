# Imagen base de Python
FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    #Hacer match con el numero de cores/núcleo de la maquina - Programación paralela
    GUNICORN_WORKERS=4 \ 
    #Hacer match con el numero de threads de la maquina - Programación concurrente
    GUNICORN_THREADS=2 \ 
    GUNICORN_TIMEOUT=120

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn && \
    pip install --no-cache-dir gunicorn

# Copiar el código fuente
COPY . .

# Exposición del puerto
EXPOSE ${PORT}

# Establecer comando de inicio usando Gunicorn #Crear el archivo wsgi.py
CMD gunicorn --config gunicorn_config.py app.main:app

#Investigar clean architecture
#Capa domanin
#Capa data
#Capa application // Logica de negocio
#Capa presentation

#Investigar SOLID
#Investigar DDD
#Investigar un concepto en donde la capa de controlador no se habla
#con la de data, si no que habla con la capa de application
#Investigar un concepto en donde la capa de controlador no se habla
#con la de data, si no que habla con la capa de application
#Investigar un concepto en donde la capa de controlador no se habla
#con la de data, si no que habla con la capa de application
#Investigar un concepto en donde la capa de controlador no se habla
#con la de data, si no que habla con la capa de application