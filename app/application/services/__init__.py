"""Configuración de Gunicorn para la aplicación."""
import os
import multiprocessing

# Configuración básica
bind = f"{os.getenv('WEBHOOK_HOST', '0.0.0.0')}:{os.getenv('WEBHOOK_PORT', '8000')}"
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv('GUNICORN_THREADS', '2'))
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
worker_class = 'uvicorn.workers.UvicornWorker'

# Configuración de logs
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Configuración para FastAPI con prefijo
if os.getenv('ROOT_PATH'):
    raw_env = [f"ROOT_PATH={os.getenv('ROOT_PATH')}"]



