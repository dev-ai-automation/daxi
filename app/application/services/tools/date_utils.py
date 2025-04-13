"""
Utilidades para el manejo de fechas y zonas horarias.
Este módulo contiene funciones para el manejo de fechas, conversiones, y formato.
"""
#Internlization/i18n y localization/l10n ⚠️ 
#Forma ya estandarizada para manejar diferentes idiomas 🦾
#Investigar internacionalización y localización 🧑‍💻
#Forma para fechas, horas, monedas, etc. 🌐
#Link: https://www.w3.org/International/O-charset-lang.html
#Crear funcion en donde reciba como parametro el idioma y devuelva la fecha en el idioma seleccionado
#Python internacionalization library: pytz, babel, etc. 📚

import re
import pytz
import calendar
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Tuple, Optional
from app.infrastructure.config.config.settings import TimeZones, TIMEZONE_MAP, DEFAULT_TIMEZONE

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
    slots_by_date: dict, 
    max_days: int = 3,
    max_slots_per_day: int = 3
) -> list:
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

def create_readable_slots(formatted_slots: list, emoji: str = "🕓") -> list:
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