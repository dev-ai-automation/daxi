"""
Rutas y endpoints del webhook.
Define los endpoints HTTP para recibir y procesar mensajes externos.
"""
#Esta sería mi capa de presentación/controlador ⚡

import os
import hmac
import hashlib
import json
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Header, Body, BackgroundTasks
from fastapi.responses import JSONResponse

from app.infrastructure.config.config.settings import WEBHOOK_SECRET
from app.domain.entities.models import WebhookMessage, WebhookResponse, AgentRequest
from app.agents.tourism_agent import tourism_agent
from app.presentation.webhook.processors import process_message, validate_signature

# Crear router para los endpoints del webhook
router = APIRouter(prefix="/webhook", tags=["webhook"])

# Constantes para seguridad y rendimiento
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB
REQUEST_TIMEOUT = 10  # 10 segundos
RATE_LIMIT = 50  # 50 solicitudes por minuto
RATE_WINDOW = 60  # Ventana de 60 segundos

# Control de tasa de solicitudes (rate limiting)
request_history = {}

def check_rate_limit(client_ip: str) -> bool:
    """
    Verifica si una IP ha excedido el límite de solicitudes.
    
    Args:
        client_ip: Dirección IP del cliente
        
    Returns:
        True si está dentro del límite, False si excede
    """
    current_time = int(time.time())
    
    # Limpiar entradas antiguas
    for ip in list(request_history.keys()):
        request_history[ip] = [ts for ts in request_history[ip] if ts > current_time - RATE_WINDOW]
        if not request_history[ip]:
            del request_history[ip]
    
    # Verificar la IP actual
    if client_ip not in request_history:
        request_history[client_ip] = []
    
    # Contar solicitudes en la ventana de tiempo
    count = len(request_history[client_ip])
    
    # Permitir si está dentro del límite
    if count < RATE_LIMIT:
        request_history[client_ip].append(current_time)
        return True
        
    return False

async def verify_webhook_request(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Verifica la firma del webhook y extrae el payload.
    
    Args:
        request: Objeto Request de FastAPI
        x_webhook_signature: Firma del webhook en header
        
    Returns:
        Payload JSON verificado
        
    Raises:
        HTTPException: Si la solicitud no es válida
    """
    # Verificar firma
    if not x_webhook_signature:
        raise HTTPException(status_code=401, detail="Falta la firma del webhook")
    
    # Leer el cuerpo de la solicitud
    try:
        body = await request.body()
        
        # Verificar tamaño máximo
        if len(body) > MAX_PAYLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Payload demasiado grande")
        
        # Validar firma con el secreto compartido
        if not validate_signature(body, x_webhook_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Firma del webhook inválida")
        
        # Parsear JSON
        payload = json.loads(body)
        return payload
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la solicitud: {str(e)}")

@router.post("/receive", response_model=WebhookResponse)
async def receive_webhook(
    background_tasks: BackgroundTasks,
    request: Request,
    payload: Dict[str, Any] = Depends(verify_webhook_request)
):
    """
    Endpoint principal para recibir mensajes del webhook.
    
    Args:
        background_tasks: Tareas en segundo plano de FastAPI
        request: Objeto Request de FastAPI
        payload: Payload JSON verificado
        
    Returns:
        Respuesta estándar del webhook
    """
    # Verificar rate limit por IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes")
    
    # Validar que payload tiene los campos requeridos
    if "type" not in payload or "content" not in payload:
        raise HTTPException(status_code=400, detail="Faltan campos requeridos (type, content)")
    
    # Crear modelo de mensaje de webhook
    try:
        webhook_message = WebhookMessage(
            type=payload["type"],
            content=payload["content"],
            user_id=payload.get("user_id"),
            timestamp=payload.get("timestamp", datetime.now().isoformat()),
            metadata=payload.get("metadata", {})
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en la validación del mensaje: {str(e)}")
    
    # Procesar el mensaje en segundo plano para responder rápidamente
    background_tasks.add_task(process_message, webhook_message.dict())
    
    # Responder inmediatamente
    return {
        "success": True,
        "message": f"Mensaje de tipo '{webhook_message.type}' recibido y en procesamiento",
        "data": {
            "received_at": datetime.now().isoformat(),
            "message_id": webhook_message.metadata.get("id", "unknown")
        }
    }

@router.post("/query", response_model=WebhookResponse)
async def query_agent(
    request: Request,
    agent_request: AgentRequest,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Endpoint para consultar directamente al agente.
    
    Args:
        request: Objeto Request de FastAPI
        agent_request: Solicitud para el agente
        x_webhook_signature: Firma del webhook en header
        
    Returns:
        Respuesta del agente
    """
    # Verificar la firma (menos estricto para consultas directas)
    if x_webhook_signature:
        body = await request.body()
        if not validate_signature(body, x_webhook_signature, WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Firma inválida")
    
    # Verificar rate limit por IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Demasiadas solicitudes")
    
    try:
        # Consultar directamente al agente
        response = await tourism_agent.process_user_message(
            message=agent_request.message,
            user_id=agent_request.user_id or "webhook_query"
        )
        
        return {
            "success": True,
            "message": response,
            "data": {
                "query_time": datetime.now().isoformat(),
                "context": agent_request.context
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la consulta: {str(e)}")

@router.get("/health")
async def health_check():
    """Endpoint para verificar el estado del webhook."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()} 