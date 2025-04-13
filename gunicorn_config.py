"""
Configuración de Gunicorn para el servidor webhook.
Este archivo define los parámetros óptimos para ejecutar la aplicación en producción.
"""
import os
import multiprocessing

# Número de workers (procesos)
# Recomendación: 2*núcleos+1 para balance entre rendimiento y uso de recursos
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Número de threads por worker
# Útil para operaciones con I/O intensivo
threads = int(os.getenv("GUNICORN_THREADS", "4"))

# Timeout en segundos
# Tiempo máximo permitido para que un worker procese una solicitud
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Dirección y puerto en que Gunicorn escuchará
bind = os.getenv("GUNICORN_BIND", f"{os.getenv('WEBHOOK_HOST', '0.0.0.0')}:{os.getenv('WEBHOOK_PORT', '8000')}")

# Clase de worker
# UvicornWorker es específico para FastAPI/ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Tipo de worker
worker_type = "async"

# Configuración de logging
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" significa stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")    # "-" significa stderr

# Configuración de recarga automática (solo para desarrollo)
reload = os.getenv("ENVIRONMENT", "production").lower() == "development"

# Configuraciones adicionales
keepalive = 65  # Tiempo en segundos para mantener conexiones abiertas
worker_connections = 1000  # Número máximo de conexiones simultáneas
max_requests = 1000  # Reiniciar worker después de procesar este número de solicitudes
max_requests_jitter = 50  # Añadir variación aleatoria al max_requests

# Control de recursos
graceful_timeout = 30  # Tiempo de gracia para que un worker finalice
limit_request_line = 4094  # Limitar tamaño de línea de solicitud
limit_request_fields = 100  # Limitar número de headers
limit_request_field_size = 8190  # Limitar tamaño de campos de header 