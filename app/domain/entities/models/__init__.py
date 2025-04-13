"""
Exportación de todos los modelos de dominio.
Este módulo centraliza la exportación de todos los modelos para facilitar su importación.
"""
# Modelos de webhook
from app.domain.entities.models.webhook_models import (
    WebhookMessage,
    WebhookResponse
)

# Modelos de agente
from app.domain.entities.models.agent_models import (
    AgentRequest,
    AgentResponse
)

# Modelos de reservas
from app.domain.entities.models.booking_models import (
    AvailableSlot,
    SlotsResult,
    BookingResult,
    BookingRequest
)

# Modelos de errores
from app.domain.entities.models.error_models import (
    ErrorResult
)

# Exportar todos los modelos para facilitar importación
__all__ = [
    # Webhook
    'WebhookMessage', 
    'WebhookResponse',
    
    # Agente
    'AgentRequest', 
    'AgentResponse',
    
    # Reservas
    'AvailableSlot', 
    'SlotsResult', 
    'BookingResult', 
    'BookingRequest',
    
    # Errores
    'ErrorResult'
]
