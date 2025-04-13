"""
Modelos de datos para el proyecto.
Define estructuras de datos y tipos utilizados en toda la aplicación.

NOTA: Este archivo está deprecado. Por favor utilizar las importaciones directas
desde los módulos específicos o desde app.domain.entities.models.
"""
# Importamos desde los archivos específicos para mantener compatibilidad
from app.domain.entities.models.webhook_models import (
    WebhookMessage,
    WebhookResponse
)

from app.domain.entities.models.agent_models import (
    AgentRequest,
    AgentResponse
)

from app.domain.entities.models.booking_models import (
    AvailableSlot,
    SlotsResult,
    BookingResult,
    BookingRequest
)

from app.domain.entities.models.error_models import (
    ErrorResult
)

# Exportamos todos los modelos para mantener compatibilidad
__all__ = [
    'AvailableSlot',
    'SlotsResult',
    'ErrorResult',
    'BookingResult',
    'WebhookMessage',
    'WebhookResponse',
    'AgentRequest',
    'AgentResponse',
    'BookingRequest'
] 