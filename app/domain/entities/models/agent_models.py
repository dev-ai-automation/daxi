"""
Modelos específicos relacionados con el agente.
Define las estructuras de datos utilizadas en la interacción con el agente.
"""
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field

from app.domain.entities.models.booking_models import AvailableSlot

class AgentRequest(BaseModel):
    """Modelo para solicitudes al agente"""
    message: str = Field(..., description="Mensaje para el agente")
    user_id: Optional[str] = Field(None, description="ID del usuario")
    context: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional")

class AgentResponse(BaseModel):
    """Modelo para respuestas del agente"""
    response: str = Field(..., description="Respuesta del agente")
    actions: Optional[List[Dict[str, Any]]] = Field(None, description="Acciones sugeridas")
    slots: Optional[List[AvailableSlot]] = Field(None, description="Slots disponibles si aplica")
    error: Optional[str] = Field(None, description="Error si ocurrió alguno") 