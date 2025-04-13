"""
Configuración centralizada del proyecto.
Este módulo gestiona todas las variables de configuración y entorno.
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from enum import Enum, auto
import pytz

# Carga explícita del archivo .env
load_dotenv(verbose=True)

# Enumeración de zonas horarias soportadas
class TimeZones(Enum):
    """Enumeración de zonas horarias soportadas (escalable para futuros añadidos)"""
    MEXICO = auto()
    # Preparado para añadir más zonas horarias en el futuro

# Mapa de zonas horarias
TIMEZONE_MAP = {
    TimeZones.MEXICO: "America/Mexico_City",
}

# Configuración por defecto
DEFAULT_TIMEZONE = TimeZones.MEXICO

# Configuración de Cal.com
CALCOM_API_KEY = os.getenv("CALCOM_API_KEY")
CALCOM_EVENT_TYPE_ID = os.getenv("CALCOM_EVENT_TYPE_ID")
CALCOM_USERNAME = os.getenv("CALCOM_USERNAME")
CALCOM_USEREMAIL = os.getenv("CALCOM_USEREMAIL")

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configuración del Webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "mi_clave_secreta_para_webhook")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

# Función para obtener la configuración como diccionario
def get_settings() -> Dict[str, Any]:
    """Retorna la configuración actual como un diccionario."""
    return {
        "calcom": {
            "api_key": CALCOM_API_KEY,
            "event_type_id": CALCOM_EVENT_TYPE_ID,
            "username": CALCOM_USERNAME,
            "user_email": CALCOM_USEREMAIL,
        },
        "supabase": {
            "url": SUPABASE_URL,
            "key": SUPABASE_KEY,
        },
        "webhook": {
            "secret": WEBHOOK_SECRET,
            "port": WEBHOOK_PORT,
            "host": WEBHOOK_HOST,
        },
        "timezone": {
            "default": TIMEZONE_MAP[DEFAULT_TIMEZONE],
        }
    } 