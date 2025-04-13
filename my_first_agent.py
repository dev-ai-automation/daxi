from agents.tool import function_tool
import aiohttp
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio
from agents import Agent, Runner
from typing import List, Dict, Optional, Union, Any, Tuple, TypedDict, Callable
import re
from dateutil.relativedelta import relativedelta
import calendar
import pytz
from functools import wraps
from enum import Enum, auto
# Importaciones para la base de datos
import uuid
from supabase import create_client, Client
from datetime import datetime, timezone

# Carga explícita del archivo .env
load_dotenv(verbose=True)

# Constantes globales
class TimeZones(Enum):
    """Enumeración de zonas horarias soportadas (escalable para futuros añadidos)"""
    MEXICO = auto()
    # Preparado para añadir más zonas horarias en el futuro
    # USA_EASTERN = auto()
    # USA_PACIFIC = auto()
    # EUROPE_CENTRAL = auto()

# Mapa de zonas horarias (fácilmente extensible)
TIMEZONE_MAP = {
    TimeZones.MEXICO: "America/Mexico_City",
    # TimeZones.USA_EASTERN: "America/New_York",
    # TimeZones.USA_PACIFIC: "America/Los_Angeles",
    # TimeZones.EUROPE_CENTRAL: "Europe/Berlin",
}

# Configuración por defecto
DEFAULT_TIMEZONE = TimeZones.MEXICO

# Clase para slots disponibles
class AvailableSlot(TypedDict):
    date: str
    start_time: str
    iso_time: str
    formatted: str

# Clase para resultado de slots
class SlotsResult(TypedDict):
    available_slots: List[AvailableSlot]
    readable_slots: List[str]
    total_slots: int
    date_query: str
    date_from: str
    date_to: str

# Clase para resultado de error
class ErrorResult(TypedDict):
    error: str
    details: Optional[str]

# Clase para resultado de reserva
class BookingResult(TypedDict):
    success: bool
    appointment_id: str
    scheduled_date: str
    scheduled_time: str
    confirmation_link: str
    message: str
    meeting_url: str  # Campo añadido para la URL de reunión

# Funciones auxiliares
def get_timezone_instance(tz: TimeZones = DEFAULT_TIMEZONE) -> pytz.timezone:
    """
    Obtiene la instancia de zona horaria basada en la enumeración.
    
    Args:
        tz: La zona horaria a utilizar (de la enumeración TimeZones)
        
    Returns:
        Instancia de pytz.timezone para la zona horaria solicitada
    """
    return pytz.timezone(TIMEZONE_MAP[tz])

def format_date_human_readable(date_obj: datetime, include_year: bool = True) -> str:
    """
    Formatea una fecha en formato legible en español.
    
    Args:
        date_obj: Objeto datetime a formatear
        include_year: Si se debe incluir el año en el formato
        
    Returns:
        Cadena formateada con la fecha en español
    """
    day_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    month_names = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    day_name = day_names[date_obj.weekday()]
    day = date_obj.day
    month = month_names[date_obj.month]
    
    if include_year:
        return f"{day_name} {day} de {month} de {date_obj.year}"
    return f"{day_name} {day} de {month}"

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

def parse_natural_date(
    date_expression: Optional[str], 
    today: datetime, 
    tz: pytz.timezone
) -> Tuple[datetime, datetime]:
    """
    Interpreta una expresión de fecha en lenguaje natural.
    
    Args:
        date_expression: Expresión de fecha en lenguaje natural
        today: Fecha actual
        tz: Zona horaria
        
    Returns:
        Tupla de (fecha_inicio, fecha_fin)
    """
    # Valores predeterminados
    start_time = today + timedelta(days=1)  # Mañana por defecto
    end_time = start_time + timedelta(days=7)  # Una semana después por defecto
    
    if not date_expression:
        return start_time, end_time
        
    date_expression = date_expression.lower().strip()
    
    # Mapeo de nombres de días en español a números (0=Lunes, 6=Domingo)
    dias = {
        'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2, 
        'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
    }
    
    # Mapeo de nombres de meses en español a números
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    # Caso 1: Expresiones relativas simples
    if "hoy" in date_expression:
        start_time = today
    elif any(expr in date_expression for expr in ["mañana", "manana"]):
        start_time = today + timedelta(days=1)
    elif any(expr in date_expression for expr in ["pasado mañana", "pasado manana"]):
        start_time = today + timedelta(days=2)
    
    # Caso 2: Próximo día de la semana (ej. "lunes próximo")
    elif any(dia in date_expression for dia in dias.keys()):
        # Encontrar qué día de la semana se mencionó
        dia_mencionado = next((dia for dia in dias.keys() if dia in date_expression), None)
        
        if dia_mencionado:
            dia_objetivo = dias[dia_mencionado]
            dias_para_sumar = (dia_objetivo - today.weekday()) % 7
            if dias_para_sumar == 0:  # Si es hoy, vamos a la próxima semana
                dias_para_sumar = 7
            start_time = today + timedelta(days=dias_para_sumar)
    
    # Caso 3: Fecha específica (ej. "31 de marzo")
    elif re.search(r'(\d+)\s+de\s+(\w+)', date_expression):
        match = re.search(r'(\d+)\s+de\s+(\w+)', date_expression)
        dia = int(match.group(1))
        mes_str = match.group(2).lower()
        
        if mes_str in meses:
            mes = meses[mes_str]
            
            # Determinar el año (este año o el próximo)
            anio = today.year
            # Si la fecha ya pasó este año, usamos el próximo año
            if mes < today.month or (mes == today.month and dia < today.day):
                anio += 1
            
            # Validar que la fecha sea válida
            try:
                dias_en_mes = calendar.monthrange(anio, mes)[1]
                if 1 <= dia <= dias_en_mes:
                    # Crear datetime sin timezone y luego localizarlo
                    naive_dt = datetime(anio, mes, dia)
                    start_time = tz.localize(naive_dt)
            except ValueError:
                pass  # Si hay error, mantenemos el valor predeterminado
    
    # Caso 4: Fecha con formato estándar (YYYY-MM-DD)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_expression):
        try:
            # Crear datetime sin timezone y luego localizarlo
            naive_dt = datetime.strptime(date_expression, "%Y-%m-%d")
            start_time = tz.localize(naive_dt)
        except ValueError:
            pass  # Si hay error, mantenemos el valor predeterminado
    
    # Buscar indicadores de rango de fechas para determinar la fecha de fin
    if "semana" in date_expression or "7 días" in date_expression or "7 dias" in date_expression:
        end_time = start_time + timedelta(days=7)
    elif "mes" in date_expression:
        end_time = start_time + relativedelta(months=1)
    else:
        # Por defecto, usamos un rango de 7 días
        end_time = start_time + timedelta(days=7)
        
    return start_time, end_time

def format_time_slots(
    slots_by_date: Dict[str, List[Dict[str, Any]]],
    max_days: int = 3,
    max_slots_per_day: int = 3
) -> List[AvailableSlot]:
    """
    Formatea y limita los slots disponibles.
    
    Args:
        slots_by_date: Diccionario de slots agrupados por fecha
        max_days: Número máximo de días a incluir
        max_slots_per_day: Número máximo de slots por día
        
    Returns:
        Lista de slots formateados y limitados
    """
    formatted_slots = []
    
    # Tomar hasta max_days días con hasta max_slots_per_day slots cada uno
    for date, slots in sorted(slots_by_date.items())[:max_days]:
        formatted_slots.extend(slots[:max_slots_per_day])
    
    # Limitar al máximo total (max_days * max_slots_per_day)
    return formatted_slots[:max_days * max_slots_per_day]

def create_readable_slots(formatted_slots: List[AvailableSlot], emoji: str = "🕓") -> List[str]:
    """
    Crea representaciones legibles de los slots disponibles.
    
    Args:
        formatted_slots: Lista de slots formateados
        emoji: Emoji a usar para cada opción
        
    Returns:
        Lista de cadenas legibles con formato atractivo
    """
    return [
        f"{emoji} *Opción {i+1}:* {format_date_human_readable(datetime.strptime(slot['date'], '%Y-%m-%d'))} "
        f"a las *{slot['start_time']}* hrs"
        for i, slot in enumerate(formatted_slots)
    ]

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

@function_tool
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
    api_key = os.getenv("CALCOM_API_KEY")
    event_type_id = os.getenv("CALCOM_EVENT_TYPE_ID")
    username = os.getenv("CALCOM_USERNAME")

    # Validar credenciales
    if not all([api_key, event_type_id, username]):
        missing_vars = [var for var, val in 
                        [("CALCOM_API_KEY", api_key), 
                         ("CALCOM_EVENT_TYPE_ID", event_type_id),
                         ("CALCOM_USERNAME", username)] 
                        if not val]
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
        "timeZone": TIMEZONE_MAP[DEFAULT_TIMEZONE]
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

@function_tool
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
    Schedule an appointment using Cal.com API based on an available time slot
    
    Args:
        option_number: The number of the slot option chosen by the user (1-based index)
        selected_date: The date for the appointment in YYYY-MM-DD format (alternative to option_number)
        selected_time: The time for the appointment in HH:MM format (alternative to option_number)
        name: The name of the person booking the appointment
        email: The email of the person booking the appointment
        notes: Optional notes for the appointment
    
    Returns:
        Confirmation details of the scheduled appointment
    """
    # Obtener credenciales y configuración
    api_key = os.getenv("CALCOM_API_KEY")
    event_type_id = os.getenv("CALCOM_EVENT_TYPE_ID")
    username = os.getenv("CALCOM_USERNAME")
    user_email = os.getenv("CALCOM_USEREMAIL")
    
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
        "timeZone": TIMEZONE_MAP[DEFAULT_TIMEZONE],
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
        
        # ID de la reserva (añadido según requerimiento)
        booking_id = booking_data.get("id", "No disponible")
        
        # URL de la reunión (añadido según requerimiento)
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

# Configuración del agente
agent = Agent(
    name="Concierge Virtual de México",
    instructions="""
    Eres un Concierge Virtual especializado en el sector de Hotelería y Turismo en México. Tu misión es ayudar a los visitantes a reservar experiencias, tours, y servicios turísticos de manera sencilla y eficiente.

    ESTILO DE COMUNICACIÓN:
    • Usa un tono cálido, hospitalario y entusiasta, típico de la hospitalidad mexicana
    • Incluye ocasionalmente frases de bienvenida en español como "¡Bienvenido!" o "¡A sus órdenes!"
    • Destaca la riqueza cultural y belleza de los destinos mexicanos
    • Sé respetuoso y profesional, manteniendo la calidez característica del servicio turístico mexicano

    INSTRUCCIONES PARA MANEJAR DISPONIBILIDAD:
    
    1. Cuando el usuario solicite información sobre disponibilidad de experiencias o tours en fechas específicas:
       - Acepta lenguaje natural como "este fin de semana", "para Semana Santa", "en puente de mayo", etc.
       - Usa la herramienta get_slots y pasa la expresión de fecha al parámetro date_expression.
    
    2. Al mostrar las primeras 03 opciones disponibles más relevantes:
       - Presenta la información usando emojis relacionados con turismo (🏖️ 🌮 🏨 🌵 🕓 🗓️)
       - Destaca las fechas y horas con formato atractivo
       - Sugiere actividades complementarias según la fecha seleccionada
       - Ejemplo: "🕓 *Opción 1:* Viernes 15 de Marzo de 2024 a las *10:00* hrs - ¡Perfecto para visitar la zona arqueológica por la mañana!"
    
    3. Después de mostrar opciones, pregunta:
       - Qué opción prefiere (por número)
       - Nombre completo para la reserva
       - Correo electrónico de contacto
       - Cualquier solicitud especial (alergias, accesibilidad, etc.)
    
    4. Al confirmar una reserva:
       - Usa un formato visualmente atractivo con emoji de confirmación ✅
       - Proporciona un resumen claro de la reserva incluyendo:
         * ID de reserva (importante: destacar esto)
         * Fecha y hora de la experiencia
         * Ubicación/enlace de reunión virtual
         * Detalles de contacto
       - Añade un consejo o recomendación turística relacionada con la fecha
       - Ofrece asistencia adicional para transporte, hospedaje u otros servicios
    
    5. En caso de errores:
       - Mantén un tono positivo y orientado a soluciones
       - Sugiere alternativas concretas
       - Usa frases como "Le ofrecemos estas alternativas..."

    IMPORTANTE: 
    • Todas las fechas y horas se manejan en horario de Ciudad de México (GMT-6)
    • Verifica que las fechas elegidas sean futuras, no pasadas
    • Destaca experiencias según temporadas (alta, baja) y eventos especiales (festivales, días festivos)
    
    FORMATO VISUAL:
    • Usa encabezados para cada sección principal
    • Emplea negritas (*texto*) para información clave
    • Incorpora emojis relevantes al turismo mexicano
    • Utiliza viñetas para listas de opciones o recomendaciones
    • Mantén respuestas concisas pero completas
    
    Recuerda que representas la hospitalidad mexicana: cálida, servicial y eficiente. ¡Haz que el viaje de cada visitante sea memorable desde la reserva!
    """,
    model="o3-mini",
    tools=[get_slots, schedule_appointment],
)

async def main():
    """
    Función principal que ejecuta el loop de conversación con el agente,
    guardando el historial en una base de datos vectorial (Supabase).
    """
    
    # Configuración de Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    # Verificar las credenciales de Supabase
    if not all([supabase_url, supabase_key]):
        print("⚠️ Advertencia: Las credenciales de Supabase no están configuradas. El historial no será guardado.")
        supabase = None
    else:
        try:
            # Inicializar el cliente de Supabase
            supabase: Client = create_client(supabase_url, supabase_key)
            print("✅ Conexión a Supabase establecida correctamente.")
        except Exception as e:
            print(f"⚠️ Error al conectar con Supabase: {str(e)}")
            print("⚠️ El historial no será guardado.")
            supabase = None
            
    print("¡Bienvenido! Soy su Concierge Virtual para experiencias turísticas en México. Escribe 'salir' para terminar la conversación.")
    
    # Generar un ID de conversación único
    conversation_id = str(uuid.uuid4())
    conversation_start_time = datetime.now(timezone.utc).isoformat()
    print(f"ID de sesión: {conversation_id}")
    
    # Inicializamos una lista para el historial de conversación
    conversation_history = []
    
    # Datos de usuario en caché (baja mutabilidad)
    user_profile = {}
    
    # Para mantener los slots disponibles entre turnos
    available_slots_data = []
    
    # Comandos para salir
    exit_commands = {'salir', 'exit', 'quit', 'adios', 'adiós', 'hasta luego', 'bye', 'byebye', 'chao', 'chaochao'}
    
    # Intentar cargar datos del usuario si el supabase está configurado
    if supabase:
        try:
            # Extraer información del usuario basado en algún identificador (podría ser una cookie, email, etc.)
            user_identifier = os.getenv("USER_IDENTIFIER", "")
            
            if user_identifier:
                # Buscar perfil del usuario en la tabla de perfiles
                user_data = supabase.table("user_profiles").select("*").eq("identifier", user_identifier).execute()
                
                if user_data.data and len(user_data.data) > 0:
                    user_profile = user_data.data[0]
                    print(f"✅ Datos de usuario cargados para: {user_profile.get('name', 'Usuario')}")
                    
                    # Añadir el contexto del usuario a la conversación
                    user_context = {
                        "role": "system",
                        "content": (
                            f"Información del usuario:\n"
                            f"- Nombre: {user_profile.get('name', 'No disponible')}\n"
                            f"- Email: {user_profile.get('email', 'No disponible')}\n"
                            f"- Preferencias: {user_profile.get('preferences', 'No disponible')}\n"
                        )
                    }
                    conversation_history.append(user_context)
                
                # Cargar el historial de conversaciones recientes si existen
                recent_history = supabase.table("conversation_history") \
                    .select("*") \
                    .eq("user_identifier", user_identifier) \
                    .order("timestamp", desc=True) \
                    .limit(1) \
                    .execute()
                
                if recent_history.data and len(recent_history.data) > 0:
                    last_conversation = recent_history.data[0]
                    last_conversation_time = datetime.fromisoformat(last_conversation['timestamp'])
                    now = datetime.now(timezone.utc)
                    
                    # Si la última conversación fue hace menos de 24 horas, añadir un resumen al contexto
                    if (now - last_conversation_time).total_seconds() < 86400:  # 24 horas
                        conversation_history.append({
                            "role": "system",
                            "content": f"Resumen de la última conversación: {last_conversation.get('summary', 'No disponible')}"
                        })
        except Exception as e:
            print(f"⚠️ Error al cargar datos de usuario: {str(e)}")
    
    async def save_conversation_turn(user_message, agent_response):
        """Guarda un turno de conversación en la base de datos vectorial"""
        if not supabase:
            return
            
        try:
            # Verificar si user_identifier existe
            user_identifier = user_profile.get("identifier", "anonymous")
            print(f"ID de usuario para guardar: {user_identifier}")
            
            # Datos para guardar
            conversation_data = {
                "conversation_id": conversation_id,
                "user_identifier": user_identifier,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_message": user_message,
                "agent_response": agent_response,
                "metadata": {
                    "available_slots": len(available_slots_data),
                    "has_user_profile": bool(user_profile)
                }
            }
            
            print(f"Intentando guardar datos en conversation_history...")
            # Guardar en la tabla de historial
            response = supabase.table("conversation_history").insert(conversation_data).execute()
            print(f"Respuesta de Supabase: {response}")
        except Exception as e:
            print(f"⚠️ Error al guardar conversación: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Ciclo principal de conversación
    while True:
        # Obtenemos el mensaje del usuario con prompt contextual
        prompt = "¿Cómo puedo ayudarle hoy? " if not conversation_history else "¿En qué más puedo asistirle? "
        message = input(prompt)
        
        # Verificamos si el usuario quiere salir
        if message.lower() in exit_commands:
            # Guardar resumen final de la conversación si supabase está disponible
            if supabase:
                try:
                    # Crear un resumen de la conversación con el propio agente
                    summary_input = [
                        {"role": "system", "content": "Resume brevemente esta conversación en una sola frase."},
                        *conversation_history[-10:]  # Usamos los últimos 10 mensajes para el resumen
                    ]
                    
                    summary_result = await Runner.run(agent, summary_input)
                    conversation_summary = summary_result.final_output
                    
                    # Guardar el resumen
                    supabase.table("conversation_summaries").insert({
                        "conversation_id": conversation_id,
                        "user_identifier": user_profile.get("identifier", "anonymous"),
                        "start_time": conversation_start_time,
                        "end_time": datetime.now(timezone.utc).isoformat(),
                        "summary": conversation_summary,
                        "message_count": len(conversation_history) // 2  # Aproximado
                    }).execute()
                except Exception as e:
                    print(f"⚠️ Error al guardar resumen: {str(e)}")
            
            print("¡Gracias por contactarnos! Esperamos darle la bienvenida pronto a nuestras experiencias. ¡Buen viaje!")
            break
        
        try:
            # Ejecutamos el agente con el mensaje apropiado
            result = await Runner.run(
                agent, 
                conversation_history + [{"role": "user", "content": message}] if conversation_history else message
            )
            
            # Extraer datos potencialmente persistentes del mensaje del usuario
            # Esto permite actualizar automáticamente información del usuario que no cambia frecuentemente
            user_data_patterns = {
                "name": r"(?:me\s+llamo|soy|nombre\s+es)\s+([A-Za-zÀ-ÿ\s]+)(?:\.|,|\s|$)",
                "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                "phone": r"(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
            }
            
            detected_user_data = {}
            for key, pattern in user_data_patterns.items():
                match = re.search(pattern, message)
                if match and key == "name":
                    detected_user_data[key] = match.group(1).strip()
                elif match:
                    detected_user_data[key] = match.group(0)
            
            # Actualizar la información del usuario en caché y potencialmente en BD
            if detected_user_data and supabase and user_profile.get("identifier"):
                user_profile.update(detected_user_data)
                try:
                    supabase.table("user_profiles").update(detected_user_data) \
                        .eq("identifier", user_profile["identifier"]) \
                        .execute()
                except Exception as e:
                    print(f"⚠️ Error al actualizar perfil: {str(e)}")
            
            # Actualizamos el contexto de slots disponibles si se llamó a get_slots
            tool_calls = [item for item in result.new_items 
                         if hasattr(item, 'tool_call') and item.tool_call]
            
            for item in tool_calls:
                if item.tool_call.name == "get_slots" and hasattr(item, 'tool_result'):
                    tool_result = item.tool_result
                    if isinstance(tool_result, dict) and 'available_slots' in tool_result:
                        available_slots_data = tool_result['available_slots']
                        
                        # Detectar selección de opción por número en el mensaje del usuario
                        option_match = re.search(r'\bopci[oó]n\s+(\d+)\b|\b(\d+)\b', message.lower())
                        if option_match:
                            option_num = int(option_match.group(1) or option_match.group(2))
                            if 1 <= option_num <= len(available_slots_data):
                                selected_slot = available_slots_data[option_num-1]
            
            # Mostramos la respuesta del agente
            print(result.final_output)
            
            # Guardar el turno de conversación en la base de datos
            await save_conversation_turn(message, result.final_output)
            
            # Actualizamos el historial de conversación para la próxima interacción
            conversation_history = result.to_input_list()
            
            # Añadimos información sobre los slots disponibles para la siguiente interacción
            if available_slots_data:
                # Extraemos solo la fecha y hora para simplificar usando list comprehension
                simple_slots = [
                    {"date": slot["date"], "time": slot["start_time"]} 
                    for slot in available_slots_data[:9]  # Limitamos a 9 slots
                ]
                
                # Añadimos esta información al contexto del sistema
                context_message = f"Disponibilidades actuales: {simple_slots}"
                conversation_history.append({"role": "system", "content": context_message})
                
        except Exception as e:
            error_message = f"Lo siento, hemos encontrado un error inesperado: {str(e)}"
            print(error_message)
            
            # En desarrollo podemos mostrar el traceback completo
            import traceback
            traceback.print_exc()
            
            # Añadir mensaje de error al contexto para que el agente pueda responder adecuadamente
            conversation_history.append({"role": "system", "content": f"Error: {error_message}"})
            continue

if __name__ == "__main__":
    asyncio.run(main())