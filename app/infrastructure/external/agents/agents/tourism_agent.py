"""
Agente principal de turismo.
Este módulo define la configuración y funcionalidad del agente conversacional de turismo.
"""
import asyncio
import uuid
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Union
from agents import Agent, Runner

from app.application.services.tools.calendar_tools import get_slots, schedule_appointment
from app.services.supabase_service import supabase_service

class TourismAgent:
    """
    Clase que encapsula la funcionalidad del agente de turismo.
    Gestiona la conversación, el contexto y la interacción con servicios externos.
    """
    
    def __init__(self):
        """Inicializa el agente de turismo."""
        self.agent = self._configure_agent()
        self.conversation_id = str(uuid.uuid4())
        self.conversation_start_time = datetime.now(timezone.utc).isoformat()
        self.conversation_history = []
        self.user_profile = {}
        self.available_slots_data = []
        self.exit_commands = {'salir', 'exit', 'quit', 'adios', 'adiós', 'hasta luego', 'bye', 'byebye', 'chao', 'chaochao'}
    
    def _configure_agent(self) -> Agent:
        """
        Configura el agente con instrucciones y herramientas.
        
        Returns:
            Instancia configurada del agente
        """
        return Agent(
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
            
            PROCESAMIENTO DE DATOS DEL WEBHOOK:
            • Cuando recibas datos del webhook, procésalos según el tipo de mensaje
            • Para mensajes de tipo "reservation_update", informa al usuario sobre cambios en su reserva
            • Para mensajes de tipo "promo", presenta ofertas especiales al usuario
            • Para mensajes de tipo "user_info", actualiza datos del perfil del usuario
            
            Recuerda que representas la hospitalidad mexicana: cálida, servicial y eficiente. ¡Haz que el viaje de cada visitante sea memorable desde la reserva!
            """,
            model="o3-mini",
            tools=[get_slots, schedule_appointment],
        )
    
    async def process_webhook_data(self, webhook_data: Dict[str, Any]) -> str:
        """
        Procesa datos recibidos del webhook y genera una respuesta adecuada.
        
        Args:
            webhook_data: Datos JSON recibidos por el webhook
            
        Returns:
            Mensaje de respuesta generado por el agente
        """
        # Validar y extraer tipo de mensaje
        message_type = webhook_data.get("type", "unknown")
        content = webhook_data.get("content", "")
        user_id = webhook_data.get("user_id", "anonymous")
        
        # Crear mensaje para el agente con formato específico según el tipo
        system_message = {
            "role": "system", 
            "content": f"Procesando mensaje de webhook de tipo '{message_type}'. "
        }
        
        # Mensaje específico según tipo
        if message_type == "reservation_update":
            system_message["content"] += f"Hay una actualización en la reserva: {content}"
        elif message_type == "promo":
            system_message["content"] += f"Hay una promoción especial para compartir: {content}"
        elif message_type == "user_info":
            system_message["content"] += f"Se ha recibido nueva información del usuario: {content}"
        else:
            system_message["content"] += f"Mensaje recibido: {content}"
        
        # Añadir mensaje al historial
        if self.conversation_history:
            history_with_new_message = self.conversation_history + [system_message]
        else:
            history_with_new_message = [system_message]
        
        # Ejecutar el agente con el mensaje nuevo
        result = await Runner.run(self.agent, history_with_new_message)
        
        # Actualizar historial
        self.conversation_history = result.to_input_list()
        
        # Guardar en Supabase si está disponible
        if user_id:
            await supabase_service.save_conversation_turn(
                conversation_id=self.conversation_id,
                user_identifier=user_id,
                user_message=f"WEBHOOK: {message_type}",
                agent_response=result.final_output,
                metadata={"webhook_data": webhook_data}
            )
            
        return result.final_output
    
    async def process_user_message(self, message: str, user_id: str = "anonymous") -> str:
        """
        Procesa un mensaje de usuario y genera una respuesta.
        
        Args:
            message: Mensaje del usuario
            user_id: ID del usuario (opcional)
            
        Returns:
            Respuesta generada por el agente
        """
        # Verificar si el usuario quiere salir
        if message.lower() in self.exit_commands:
            return "¡Gracias por contactarnos! Esperamos darle la bienvenida pronto a nuestras experiencias. ¡Buen viaje!"
        
        # Extraer datos potencialmente persistentes del mensaje del usuario
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
        
        # Actualizar la información del usuario y guardarlo si es posible
        if detected_user_data and user_id != "anonymous":
            self.user_profile.update(detected_user_data)
            await supabase_service.update_user_profile(user_id, detected_user_data)
        
        # Ejecutar el agente con el mensaje del usuario
        input_list = self.conversation_history + [{"role": "user", "content": message}] if self.conversation_history else [{"role": "user", "content": message}]
        result = await Runner.run(self.agent, input_list)
        
        # Actualizar historial de conversación
        self.conversation_history = result.to_input_list()
        
        # Detectar si se obtuvieron slots disponibles
        tool_calls = [item for item in result.new_items 
                     if hasattr(item, 'tool_call') and item.tool_call]
        
        for item in tool_calls:
            if item.tool_call.name == "get_slots" and hasattr(item, 'tool_result'):
                tool_result = item.tool_result
                if isinstance(tool_result, dict) and 'available_slots' in tool_result:
                    self.available_slots_data = tool_result['available_slots']
                    
        # Guardar en Supabase
        await supabase_service.save_conversation_turn(
            conversation_id=self.conversation_id,
            user_identifier=user_id,
            user_message=message,
            agent_response=result.final_output,
            metadata={"available_slots": len(self.available_slots_data)}
        )
        
        # Añadir información sobre los slots disponibles para la siguiente interacción
        if self.available_slots_data:
            # Extraemos solo la fecha y hora para simplificar usando list comprehension
            simple_slots = [
                {"date": slot["date"], "time": slot["start_time"]} 
                for slot in self.available_slots_data[:9]  # Limitamos a 9 slots
            ]
            
            # Añadimos esta información al contexto del sistema
            context_message = f"Disponibilidades actuales: {simple_slots}"
            self.conversation_history.append({"role": "system", "content": context_message})
            
        return result.final_output
    
    async def save_conversation_summary(self) -> None:
        """Guarda un resumen de la conversación actual en Supabase."""
        if len(self.conversation_history) < 2:
            return
            
        try:
            # Crear un resumen de la conversación con el propio agente
            summary_input = [
                {"role": "system", "content": "Resume brevemente esta conversación en una sola frase."},
                *self.conversation_history[-10:]  # Usamos los últimos 10 mensajes para el resumen
            ]
            
            summary_result = await Runner.run(self.agent, summary_input)
            conversation_summary = summary_result.final_output
            
            # Obtener user_identifier
            user_identifier = self.user_profile.get("identifier", "anonymous")
            
            # Guardar el resumen
            await supabase_service.save_conversation_summary(
                conversation_id=self.conversation_id,
                user_identifier=user_identifier,
                summary=conversation_summary,
                start_time=self.conversation_start_time,
                end_time=datetime.now(timezone.utc).isoformat(),
                message_count=len(self.conversation_history) // 2  # Aproximado
            )
        except Exception as e:
            print(f"⚠️ Error al guardar resumen: {str(e)}")
            
# Instancia global del agente
tourism_agent = TourismAgent() 