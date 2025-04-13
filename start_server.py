#!/usr/bin/env python
"""
Script para iniciar el servidor Gunicorn con la configuración adecuada.
Facilita el arranque del servidor en diferentes entornos.
"""
#Este archivo es para iniciar el servidor Gunicorn con la configuración adecuada.
#Facilita el arranque del servidor en diferentes entornos.
#Este archiv es el bueno 💯

#$30 USD por horas con un maximo de 3 horas/semana 💰
#Planeacion por semana ⏰


import os
import sys
import subprocess
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("start_server")

def main():
    """Función principal para iniciar el servidor Gunicorn."""
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar que Gunicorn está instalado
    try:
        import gunicorn
    except ImportError:
        logger.error("Gunicorn no está instalado. Por favor, instala las dependencias con 'pip install -r requirements.txt'")
        sys.exit(1)
    
    # Verificar que el archivo de configuración existe
    if not os.path.exists("gunicorn_config.py"):
        logger.error("El archivo de configuración de Gunicorn no existe. Asegúrate de que estás en el directorio correcto.")
        sys.exit(1)
    
    # Verificar que la aplicación existe
    try:
        from app.main import app
        logger.info("Aplicación cargada correctamente")
    except ImportError:
        logger.error("No se pudo cargar la aplicación. Verifica la estructura del proyecto.")
        sys.exit(1)
    
    # Obtener valores de configuración
    port = os.getenv("WEBHOOK_PORT", "8000")
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    workers = os.getenv("GUNICORN_WORKERS", "4")
    threads = os.getenv("GUNICORN_THREADS", "2")
    environment = os.getenv("ENVIRONMENT", "development")
    root_path = os.getenv("ROOT_PATH", "")
    
    # Mostrar configuración
    logger.info(f"Iniciando servidor en {host}:{port}")
    logger.info(f"Entorno: {environment}")
    logger.info(f"Workers: {workers}, Threads: {threads}")
    
    if root_path:
        logger.info(f"ROOT_PATH configurado como: {root_path}")
        logger.info(f"La API estará disponible en: http://{host}:{port}{root_path}/docs")
    else:
        logger.info(f"La API estará disponible en: http://{host}:{port}/docs")
    
    # Comando para iniciar Gunicorn
    cmd = [
        "gunicorn",
        "--config", "gunicorn_config.py",
        "app.main:app"
    ]
    
    # Ejecutar Gunicorn
    try:
        logger.info("Iniciando Gunicorn...")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        logger.info("Servidor detenido manualmente")
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 