"""
Modelos específicos relacionados con el webhook.
Define las estructuras de datos utilizadas en la comunicación del webhook.
"""
from typing import Dict, Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

class WebhookMessage(BaseModel):
    """Modelo de mensaje recibido por el webhook"""
    type: str = Field(..., description="Tipo de mensaje recibido")
    content: str = Field(..., description="Contenido del mensaje")
    user_id: Optional[str] = Field(None, description="ID del usuario que envía el mensaje")
    timestamp: Optional[datetime] = Field(None, description="Timestamp del mensaje")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos adicionales")

class WebhookResponse(BaseModel):
    """Modelo de respuesta del webhook"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje de la respuesta")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales") 