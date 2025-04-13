"""
Herramientas para interactuar con calendarios y APIs de reserva.
Este módulo contiene funciones para obtener slots disponibles y gestionar reservas.
"""
#Debería de estar en la capa de data/services/repository ⚠️

import json
import aiohttp
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple, TypedDict, Callable
from functools import wraps

from app.domain.entities.models import (
    AvailableSlot, SlotsResult, ErrorResult, BookingResult
)
from app.application.services.tools.date_utils import (
    get_timezone_instance, parse_natural_date, 
    format_time_slots, create_readable_slots, format_date_human_readable
)
from app.infrastructure.config.config.settings import TimeZones, DEFAULT_TIMEZONE, get_settings

# Decorador para manejo de errores en herramientas
def handle_tool_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return {
                "error": f"Error en la operación: {str(e)}",
                "details": f"Ocurrió un error inesperado en {func.__name__}"
            }
    return wrapper

async def api_request(
    method: str, 
    url: str, 
    params: Optional[Dict[str, Any]] = None, 
    headers: Optional[Dict[str, str]] = None, 
    data: Optional[Dict[str, Any]] = None
) -> Tuple[int, Any]:
    """
    Función genérica para realizar solicitudes a APIs.
    
    Args:
        method: Método HTTP (get, post, etc.)
        url: URL de la solicitud
        params: Parámetros de la solicitud
        headers: Cabeceras de la solicitud
        data: Datos para métodos POST/PUT/PATCH
        
    Returns:
        Tupla con (código_respuesta, datos_json)
    """
    async with aiohttp.ClientSession() as session:
        method_func = getattr(session, method.lower())
        
        kwargs = {}
        if params:
            kwargs['params'] = params
        if headers:
            kwargs['headers'] = headers
        if data:
            kwargs['data'] = json.dumps(data)
            
        async with method_func(url, **kwargs) as response:
            try:
                response_data = await response.json()
            except:
                response_text = await response.text()
                response_data = {"text": response_text}
                
            return response.status, response_data

@handle_tool_errors
async def get_slots(date_expression: str = None) -> Union[SlotsResult, ErrorResult]:
    """
    Obtiene los slots disponibles para reservar citas usando la API de Cal.com

    Args:
        date_expression: Expresión de fecha en lenguaje natural (ej. "mañana", "lunes", "31 de marzo").
                        Por defecto se usará mañana.

    Returns:
        Los slots disponibles formateados para mostrar al usuario
    """
    # Obtener credenciales y configuración
    settings = get_settings()
    api_key = settings["calcom"]["api_key"]
    event_type_id = settings["calcom"]["event_type_id"]
    username = settings["calcom"]["username"]

    # Validar credenciales
    if not all([api_key, event_type_id, username]):
        missing_vars = []
        if not api_key:
            missing_vars.append("CALCOM_API_KEY")
        if not event_type_id:
            missing_vars.append("CALCOM_EVENT_TYPE_ID")
        if not username:
            missing_vars.append("CALCOM_USERNAME")
        return {"error": f"Faltan variables de entorno: {', '.join(missing_vars)}"}

    # Configurar zona horaria y fecha actual
    mexico_tz = get_timezone_instance(TimeZones.MEXICO)
    today = datetime.now(mexico_tz)
    
    # Interpretar expresión de fecha en lenguaje natural
    start_time, end_time = parse_natural_date(date_expression, today, mexico_tz)
    
    # Configurar parámetros para la API
    url = "https://api.cal.com/v1/slots"
    params = {
        "apiKey": api_key,
        "eventTypeId": event_type_id,
        "startTime": start_time.strftime("%Y-%m-%d"),
        "endTime": end_time.strftime("%Y-%m-%d"),
        "timeZone": settings["timezone"]["default"]
    }

    # Realizar solicitud a la API
    status_code, data = await api_request("get", url, params=params)
    
    if status_code != 200:
        error_details = data.get("text", str(data)) if isinstance(data, dict) else str(data)
        return {"error": f"Error al obtener disponibilidad: {status_code}", "details": error_details}
    
    # Procesar los slots disponibles
    available_slots = []
    slots_by_date = {}
                    
    # Extraer y procesar todos los slots disponibles
    for day, slots in data.get("slots", {}).items():
        day_slots = []
        for slot in slots:
            time_str = slot.get("time")
            if not time_str:
                continue
                
            # Convertir la hora a un formato estándar
            try:
                # Intentar diferentes formatos de hora
                if '+' in time_str or '-' in time_str:
                    time_dt = datetime.fromisoformat(time_str)
                else:
                    time_dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Último intento con formato simple
                    date_part = day
                    time_part = time_str.split('T')[1] if 'T' in time_str else time_str
                    time_dt = datetime.strptime(f"{date_part} {time_part.split('+')[0].split('-')[0]}", "%Y-%m-%d %H:%M:%S")
                except:
                    # Si falla, omitimos este slot
                    continue
            
            # Añadir slot procesado
            slot_info = {
                "date": day,
                "start_time": time_dt.strftime("%H:%M"),
                "iso_time": time_str,
                "formatted": time_dt.strftime("%H:%M")
            }
            
            day_slots.append(slot_info)
        
        # Si hay slots para este día, los añadimos al diccionario
        if day_slots:
            slots_by_date[day] = day_slots
    
    # Formatear y limitar los slots
    formatted_slots = format_time_slots(slots_by_date)
    
    # Si no hay slots disponibles después del procesamiento
    if not formatted_slots:
        return {
            "error": "No hay disponibilidad para las fechas seleccionadas.",
            "date_query": date_expression if date_expression else "próximos días",
            "date_from": start_time.strftime("%Y-%m-%d"),
            "date_to": end_time.strftime("%Y-%m-%d")
        }
    
    # Crear slots legibles para el usuario
    readable_slots = create_readable_slots(formatted_slots)
    
    # Construir respuesta
    return {
        "available_slots": formatted_slots,
        "readable_slots": readable_slots,
        "total_slots": len(formatted_slots),
        "date_query": date_expression if date_expression else "próximos días",
        "date_from": start_time.strftime("%Y-%m-%d"),
        "date_to": end_time.strftime("%Y-%m-%d")
    }

@handle_tool_errors
async def schedule_appointment(
    option_number: Optional[int] = None, 
    selected_date: Optional[str] = None, 
    selected_time: Optional[str] = None, 
    name: str = None, 
    email: str = None, 
    notes: Optional[str] = None
) -> Union[BookingResult, ErrorResult]:
    """
    Programa una cita usando la API de Cal.com basada en un slot de tiempo disponible
    
    Args:
        option_number: El número de la opción de slot elegida por el usuario (índice base 1)
        selected_date: La fecha para la cita en formato YYYY-MM-DD (alternativa a option_number)
        selected_time: La hora para la cita en formato HH:MM (alternativa a option_number)
        name: El nombre de la persona que reserva la cita
        email: El correo de la persona que reserva la cita
        notes: Notas opcionales para la cita
    
    Returns:
        Detalles de confirmación de la cita programada
    """
    # Obtener credenciales y configuración
    settings = get_settings()
    api_key = settings["calcom"]["api_key"]
    event_type_id = settings["calcom"]["event_type_id"]
    username = settings["calcom"]["username"]
    user_email = settings["calcom"]["user_email"]
    
    # Validar credenciales
    required_vars = {
        "CALCOM_API_KEY": api_key,
        "CALCOM_EVENT_TYPE_ID": event_type_id,
        "CALCOM_USERNAME": username,
        "CALCOM_USEREMAIL": user_email
    }
    
    missing_vars = [name for name, value in required_vars.items() if not value]
    if missing_vars:
        return {"error": f"Faltan variables de entorno: {', '.join(missing_vars)}"}
    
    # Validar datos del usuario
    if not name or not email:
        return {
            "error": "Información incompleta",
            "details": "Se requiere nombre y correo electrónico para agendar la reserva."
        }
    
    # Validar datos de la cita
    if not selected_date or not selected_time:
        return {
            "error": "Información incompleta", 
            "details": "Se requiere fecha y hora para agendar la reserva."
        }
    
    # Formatear fecha y hora para la API
    try:
        # Obtener zona horaria de México
        mexico_tz = get_timezone_instance(TimeZones.MEXICO)
        
        # Crear objeto datetime para la hora de inicio con zona horaria de México
        naive_dt = datetime.strptime(f"{selected_date}T{selected_time}", "%Y-%m-%dT%H:%M")
        mexico_dt = mexico_tz.localize(naive_dt)
        
        # Verificar que la fecha está en el futuro
        now = datetime.now(mexico_tz)
        if mexico_dt < now:
            return {
                "error": "La cita seleccionada se encuentra en el pasado.",
                "details": "Por favor seleccione una fecha y hora futuras."
            }
        
        # Calcular hora de finalización (30 minutos después)
        end_time = mexico_dt + timedelta(minutes=30)
        
        # Formatear para la API manteniendo la zona horaria
        start_iso = mexico_dt.isoformat()
        end_iso = end_time.isoformat()
    except ValueError:
        return {"error": "Formato de fecha u hora inválido. Use YYYY-MM-DD para fecha y HH:MM para hora."}
    
    # Configurar la solicitud para la API
    booking_url = f"https://api.cal.com/v1/bookings?apiKey={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Configurar payload según la estructura esperada por la API
    payload = {
        "eventTypeId": int(event_type_id),
        "username": username,
        "useremail": user_email,
        "start": start_iso,
        "end": end_iso,
        "responses": {
            "name": name,
            "email": email
        },
        "tittle": "Reserva de Experiencia Turística",  # Adaptado para turismo
        "metadata": {
            "source": "asistente_turismo",
            "notes": notes or ""
        },
        "timeZone": settings["timezone"]["default"],
        "language": "es"
    }
    
    # Realizar la solicitud a la API
    status_code, booking_data = await api_request("post", booking_url, headers=headers, data=payload)
    
    # Procesar la respuesta
    if status_code in (200, 201):
        # Asegurar que booking_data es un diccionario
        if not isinstance(booking_data, dict):
            try:
                booking_data = json.loads(booking_data)
            except:
                booking_data = {"message": "Reserva exitosa pero respuesta no procesable"}
        
        # Formatear la fecha para mostrarla de forma amigable
        date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
        formatted_date = format_date_human_readable(date_obj)
        
        # ID de la reserva
        booking_id = booking_data.get("id", "No disponible")
        
        # URL de la reunión
        # Por ahora es una URL simulada de Google Meet, en el futuro podría venir de la API
        meeting_url = "https://meet.google.com/abc-defg-hij"
        
        return {
            "success": True,
            "appointment_id": booking_id,
            "scheduled_date": formatted_date,
            "scheduled_time": selected_time,
            "confirmation_link": booking_data.get("confirmationLink", ""),
            "message": "✅ *¡Reserva confirmada exitosamente!*",
            "meeting_url": meeting_url
        }
    else:
        # Extraer detalles del error
        error_details = ""
        if isinstance(booking_data, dict) and "text" in booking_data:
            error_details = booking_data["text"]
        elif isinstance(booking_data, str):
            error_details = booking_data
        else:
            error_details = json.dumps(booking_data)
            
        return {
            "error": f"❌ Error al programar la reserva: {status_code}",
            "details": error_details
        } 