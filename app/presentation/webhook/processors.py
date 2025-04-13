"""
Procesadores y validadores para el webhook.
Este módulo contiene las funciones para procesar y validar los mensajes recibidos por el webhook.
"""
#Necesito que hagas "x" en donde le diga mi estructura de carpetas, la responsabilidade mis capas y
#volver más eficiente el codigo 🧙‍♂️

import hmac
import hashlib
import json
import logging
import asyncio
from typing import Dict, Any, Callable, Optional

from app.agents.tourism_agent import tourism_agent

# Configurar logging
logger = logging.getLogger("webhook")

def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Valida la firma HMAC de un payload.
    
    Esta función implementa el método estándar de autenticación de webhook basado en HMAC.
    El emisor del webhook firma el payload con una clave compartida, y el receptor
    puede verificar la firma para asegurar que el mensaje es auténtico.
    
    Args:
        payload: Payload del webhook en bytes
        signature: Firma proporcionada en el header
        secret: Clave secreta compartida
        
    Returns:
        True si la firma es válida, False en caso contrario
    """
    # Verificar que tenemos los datos necesarios
    if not payload or not signature or not secret:
        logger.warning("Faltan datos para validar la firma")
        return False
    
    # Calcular firma esperada
    try:
        # Convertir secret a bytes si es string
        if isinstance(secret, str):
            secret = secret.encode()
            
        # Calcular hash HMAC utilizando SHA-256
        calculated_hmac = hmac.new(
            secret,
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Comparar firmas (comparación de tiempo constante)
        return hmac.compare_digest(calculated_hmac, signature)
    except Exception as e:
        logger.error(f"Error al validar firma: {str(e)}")
        return False

def generate_signature(payload: Dict[str, Any], secret: str) -> str:
    """
    Genera una firma HMAC para un payload.
    
    Esta función es útil para sistemas que necesitan enviar webhooks
    firmados hacia otros servicios.
    
    Args:
        payload: Diccionario con datos a firmar
        secret: Clave secreta compartida
        
    Returns:
        Firma hexadecimal del payload
    """
    # Convertir payload a JSON y luego a bytes
    payload_bytes = json.dumps(payload).encode()
    
    # Convertir secret a bytes si es string
    if isinstance(secret, str):
        secret = secret.encode()
        
    # Calcular y retornar la firma
    return hmac.new(
        secret,
        payload_bytes,
        hashlib.sha256
    ).hexdigest()

async def process_message(message_data: Dict[str, Any]) -> None:
    """
    Procesa un mensaje recibido por el webhook.
    
    Esta función se ejecuta de forma asíncrona para evitar bloquear la respuesta
    HTTP. Realiza el procesamiento específico según el tipo de mensaje.
    
    Args:
        message_data: Datos del mensaje a procesar
    """
    try:
        # Registrar la recepción del mensaje
        logger.info(f"Procesando mensaje tipo: {message_data.get('type')}")
        
        # Validar campos mínimos
        if "type" not in message_data or "content" not in message_data:
            logger.error("Mensaje incompleto: faltan campos obligatorios")
            return
            
        # Enviar al agente para procesamiento
        response = await tourism_agent.process_webhook_data(message_data)
        
        # Registrar respuesta del agente
        logger.info(f"Agente procesó mensaje: {response[:100]}...")
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}")

def format_webhook_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatea datos para ser enviados como webhook.
    
    Esta función estandariza el formato de los datos que se enviarán
    como webhook a otros sistemas.
    
    Args:
        data: Datos a formatear
        
    Returns:
        Datos formateados según el estándar de webhook
    """
    # Estructura base del webhook
    webhook_data = {
        "type": data.get("type", "unknown"),
        "content": data.get("content", ""),
        "timestamp": data.get("timestamp"),
        "metadata": {}
    }
    
    # Añadir metadatos específicos según el tipo
    if webhook_data["type"] == "reservation_update":
        webhook_data["metadata"] = {
            "reservation_id": data.get("reservation_id"),
            "status": data.get("status"),
            "update_reason": data.get("reason")
        }
    elif webhook_data["type"] == "promo":
        webhook_data["metadata"] = {
            "promo_id": data.get("promo_id"),
            "valid_until": data.get("valid_until"),
            "discount": data.get("discount")
        }
    
    # Añadir user_id si está disponible
    if "user_id" in data:
        webhook_data["user_id"] = data["user_id"]
        
    return webhook_data

# Registro de validadores especializados por tipo de mensaje
# Esto permite añadir validaciones específicas para cada tipo de webhook
validators: Dict[str, Callable] = {} 