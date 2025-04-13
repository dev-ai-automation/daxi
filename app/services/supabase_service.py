"""
Servicio para interactuar con Supabase.
Este módulo maneja todas las operaciones relacionadas con la base de datos Supabase.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from supabase import create_client, Client

from app.infrastructure.config.config.settings import SUPABASE_URL, SUPABASE_KEY

class SupabaseService:
    """Clase para gestionar las operaciones con Supabase."""
    
    def __init__(self):
        """Inicializa el servicio de Supabase con las credenciales."""
        self.client = None
        self.connected = False
        self._connect()
    
    def _connect(self) -> None:
        """Establece la conexión con Supabase."""
        if not all([SUPABASE_URL, SUPABASE_KEY]):
            print("⚠️ Advertencia: Las credenciales de Supabase no están configuradas.")
            return
            
        try:
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            self.connected = True
            print("✅ Conexión a Supabase establecida correctamente.")
        except Exception as e:
            print(f"⚠️ Error al conectar con Supabase: {str(e)}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Verifica si la conexión está activa."""
        return self.connected and self.client is not None
    
    async def save_conversation_turn(self, 
                                    conversation_id: str,
                                    user_identifier: str,
                                    user_message: str, 
                                    agent_response: str,
                                    metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Guarda un turno de conversación en la base de datos.
        
        Args:
            conversation_id: ID único de la conversación
            user_identifier: ID del usuario
            user_message: Mensaje del usuario
            agent_response: Respuesta del agente
            metadata: Metadatos adicionales
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self.is_connected():
            return False
            
        try:
            # Datos para guardar
            conversation_data = {
                "conversation_id": conversation_id,
                "user_identifier": user_identifier,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_message": user_message,
                "agent_response": agent_response,
                "metadata": metadata or {}
            }
            
            # Guardar en la tabla de historial
            response = self.client.table("conversation_history").insert(conversation_data).execute()
            return True
        except Exception as e:
            print(f"⚠️ Error al guardar conversación: {str(e)}")
            return False
    
    async def load_user_profile(self, user_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Carga el perfil de un usuario.
        
        Args:
            user_identifier: ID del usuario
            
        Returns:
            Diccionario con los datos del usuario o None si no existe
        """
        if not self.is_connected() or not user_identifier:
            return None
            
        try:
            # Buscar perfil del usuario en la tabla de perfiles
            response = self.client.table("user_profiles").select("*").eq("identifier", user_identifier).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"⚠️ Error al cargar perfil de usuario: {str(e)}")
            return None
    
    async def update_user_profile(self, user_identifier: str, data: Dict[str, Any]) -> bool:
        """
        Actualiza el perfil de un usuario.
        
        Args:
            user_identifier: ID del usuario
            data: Datos a actualizar
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        if not self.is_connected() or not user_identifier:
            return False
            
        try:
            # Actualizar datos del usuario
            self.client.table("user_profiles").update(data).eq("identifier", user_identifier).execute()
            return True
        except Exception as e:
            print(f"⚠️ Error al actualizar perfil de usuario: {str(e)}")
            return False
    
    async def save_conversation_summary(self, 
                                      conversation_id: str,
                                      user_identifier: str,
                                      summary: str,
                                      start_time: str,
                                      end_time: str,
                                      message_count: int) -> bool:
        """
        Guarda un resumen de conversación.
        
        Args:
            conversation_id: ID único de la conversación
            user_identifier: ID del usuario
            summary: Resumen de la conversación
            start_time: Hora de inicio de la conversación
            end_time: Hora de finalización de la conversación
            message_count: Número de mensajes en la conversación
            
        Returns:
            True si se guardó correctamente, False en caso contrario
        """
        if not self.is_connected():
            return False
            
        try:
            # Datos del resumen
            summary_data = {
                "conversation_id": conversation_id,
                "user_identifier": user_identifier,
                "start_time": start_time,
                "end_time": end_time,
                "summary": summary,
                "message_count": message_count
            }
            
            # Guardar en la tabla de resúmenes
            self.client.table("conversation_summaries").insert(summary_data).execute()
            return True
        except Exception as e:
            print(f"⚠️ Error al guardar resumen: {str(e)}")
            return False
    
    async def get_recent_conversations(self, user_identifier: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene las conversaciones recientes de un usuario.
        
        Args:
            user_identifier: ID del usuario
            limit: Número máximo de conversaciones a obtener
            
        Returns:
            Lista de conversaciones recientes
        """
        if not self.is_connected():
            return []
            
        try:
            # Buscar conversaciones recientes del usuario
            response = self.client.table("conversation_summaries") \
                .select("*") \
                .eq("user_identifier", user_identifier) \
                .order("end_time", desc=True) \
                .limit(limit) \
                .execute()
                
            return response.data if response.data else []
        except Exception as e:
            print(f"⚠️ Error al obtener conversaciones recientes: {str(e)}")
            return []
            
# Instancia global del servicio
supabase_service = SupabaseService() 