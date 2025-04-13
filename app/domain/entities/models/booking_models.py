"""
Modelos específicos relacionados con reservas y disponibilidad.
Define las estructuras de datos utilizadas en la gestión de slots y reservas.
"""
from typing import List, Dict, Optional, TypedDict
from pydantic import BaseModel, Field, EmailStr

class AvailableSlot(TypedDict):
    """Modelo para representar un slot disponible para reservar"""
    date: str
    start_time: str
    iso_time: str
    formatted: str

class SlotsResult(TypedDict):
    """Modelo para representar el resultado de una búsqueda de slots disponibles"""
    available_slots: List[AvailableSlot]
    readable_slots: List[str]
    total_slots: int
    date_query: str
    date_from: str
    date_to: str

class BookingResult(TypedDict):
    """Modelo para representar el resultado de una reserva"""
    success: bool
    appointment_id: str
    scheduled_date: str
    scheduled_time: str
    confirmation_link: str
    message: str
    meeting_url: str

class BookingRequest(BaseModel):
    """Modelo para solicitudes de reserva"""
    date: str = Field(..., description="Fecha seleccionada (YYYY-MM-DD)")
    time: str = Field(..., description="Hora seleccionada (HH:MM)")
    name: str = Field(..., description="Nombre completo")
    email: EmailStr = Field(..., description="Correo electrónico")
    notes: Optional[str] = Field(None, description="Notas adicionales") 