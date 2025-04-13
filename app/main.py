"""
Punto de entrada principal de la aplicación.
Configura y ejecuta el servidor web con FastAPI.
"""
import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.infrastructure.config.config.settings import WEBHOOK_PORT, WEBHOOK_HOST
from app.presentation.webhook.routes import router as webhook_router

# Configuración de logging con nivel configurable
log_level = os.getenv("LOG_LEVEL", "INFO")
numeric_level = getattr(logging, log_level.upper(), logging.INFO)
logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)

# Crear la aplicación FastAPI con metadatos mejorados
app = FastAPI(
    title="Tourism Agent Webhook",
    description="Webhook para procesar mensajes del agente de turismo",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH", ""),  # Para configuración de subdominios o rutas base
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "webhook", "description": "Operaciones relacionadas con el webhook"},
        {"name": "health", "description": "Verificaciones de estado del sistema"}
    ],
    contact={
        "name": "Equipo de Soporte",
        "email": "soporte@ejemplo.com"
    }
)

# Configurar CORS con orígenes específicos desde variables de entorno
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Registrar los routers
app.include_router(webhook_router)

# Manejador global de excepciones
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones."""
    logger.error(f"Error no manejado: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)}
    )

@app.get("/", tags=["health"])
async def root():
    """Endpoint principal para verificar que el servidor está funcionando."""
    return {
        "message": "Webhook del Agente de Turismo",
        "docs": "/docs",
        "status": "online"
    }

# Esta variable 'app' será utilizada por Gunicorn
# No se necesita correr uvicorn directamente ya que Gunicorn lo hará
# Esto permite que Gunicorn sirva la aplicación correctamente 