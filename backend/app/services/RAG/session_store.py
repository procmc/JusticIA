"""
Session Store para gestión de conversaciones con LangChain.

Proporciona almacenamiento en memoria para múltiples sesiones de chat,
compatible con RunnableWithMessageHistory de LangChain.
"""

from typing import Dict, List, Optional, Callable
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
import logging

logger = logging.getLogger(__name__)


class InMemoryChatMessageHistory(BaseChatMessageHistory):
    """
    Implementación de BaseChatMessageHistory para almacenamiento en memoria.
    Compatible con RunnableWithMessageHistory de LangChain.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._messages: List[BaseMessage] = []
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Obtiene los mensajes de la sesión"""
        return self._messages
    
    def add_message(self, message: BaseMessage) -> None:
        """Añade un mensaje a la sesión"""
        self._messages.append(message)
    
    def clear(self) -> None:
        """Limpia todos los mensajes de la sesión"""
        self._messages.clear()


class ConversationMetadata:
    """Metadatos de una conversación para gestión y UI"""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        created_at: datetime,
        updated_at: datetime,
        title: Optional[str] = None,
        message_count: int = 0,
        expediente_number: Optional[str] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.title = title or "Nueva conversación"
        self.message_count = message_count
        self.expediente_number = expediente_number
    
    def to_dict(self) -> dict:
        """Convierte a diccionario para serialización"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "message_count": self.message_count,
            "expediente_number": self.expediente_number
        }


class ConversationStore:
    """
    Store centralizado para gestión de múltiples conversaciones.
    
    Features:
    - Almacenamiento en memoria de sesiones
    - Índice por usuario para recuperación rápida
    - Metadatos para UI (título, fechas, contador)
    - Compatible con RunnableWithMessageHistory
    - Auto-generación de títulos
    """
    
    def __init__(self):
        # Almacenamiento principal: {session_id: InMemoryChatMessageHistory}
        self._store: Dict[str, InMemoryChatMessageHistory] = {}
        
        # Índice por usuario: {user_id: [session_ids]}
        self._user_sessions: Dict[str, List[str]] = {}
        
        # Metadatos: {session_id: ConversationMetadata}
        self._metadata: Dict[str, ConversationMetadata] = {}
        
        logger.info("ConversationStore inicializado")
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """
        Obtiene o crea el historial de una sesión.
        
        Esta es la función que se pasa a RunnableWithMessageHistory.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            BaseChatMessageHistory con los mensajes de la sesión
        """
        if session_id not in self._store:
            logger.info(f"Creando nueva sesión: {session_id}")
            self._store[session_id] = InMemoryChatMessageHistory(session_id)
            
            # Crear metadatos si no existen
            if session_id not in self._metadata:
                # Extraer user_id del session_id (formato: session_user@example.com_timestamp)
                parts = session_id.split('_')
                user_id = parts[1] if len(parts) >= 3 else 'unknown'
                
                self._create_metadata(session_id, user_id)
        
        return self._store[session_id]
    
    def _create_metadata(self, session_id: str, user_id: str) -> ConversationMetadata:
        """Crea metadatos para una nueva sesión"""
        now = datetime.utcnow()
        
        metadata = ConversationMetadata(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now
        )
        
        self._metadata[session_id] = metadata
        
        # Agregar al índice de usuario
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        
        if session_id not in self._user_sessions[user_id]:
            self._user_sessions[user_id].append(session_id)
        
        logger.info(f"Metadatos creados para sesión {session_id}")
        return metadata
    
    def update_metadata(
        self, 
        session_id: str, 
        title: Optional[str] = None,
        expediente_number: Optional[str] = None
    ):
        """Actualiza metadatos de una sesión"""
        if session_id in self._metadata:
            metadata = self._metadata[session_id]
            metadata.updated_at = datetime.utcnow()
            
            if title:
                metadata.title = title
            
            if expediente_number:
                metadata.expediente_number = expediente_number
            
            # Actualizar contador de mensajes
            if session_id in self._store:
                metadata.message_count = len(self._store[session_id].messages)
    
    def auto_generate_title(self, session_id: str):
        """Auto-genera título basado en el primer mensaje del usuario"""
        if session_id not in self._store or session_id not in self._metadata:
            return
        
        messages = self._store[session_id].messages
        
        # Buscar el primer mensaje del usuario
        for msg in messages:
            if isinstance(msg, HumanMessage) and msg.content.strip():
                # Usar los primeros 60 caracteres
                title = msg.content.strip()[:60]
                if len(msg.content) > 60:
                    title += "..."
                
                self._metadata[session_id].title = title
                logger.info(f"Título auto-generado para {session_id}: {title}")
                break
    
    def get_user_sessions(self, user_id: str) -> List[ConversationMetadata]:
        """
        Obtiene todas las sesiones de un usuario con sus metadatos.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de ConversationMetadata ordenada por fecha de actualización
        """
        session_ids = self._user_sessions.get(user_id, [])
        
        conversations = []
        for session_id in session_ids:
            if session_id in self._metadata:
                conversations.append(self._metadata[session_id])
        
        # Ordenar por fecha de actualización (más reciente primero)
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        
        logger.info(f"Usuario {user_id} tiene {len(conversations)} conversaciones")
        return conversations
    
    def get_session_detail(self, session_id: str) -> Optional[Dict]:
        """
        Obtiene el detalle completo de una sesión (metadatos + mensajes).
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con metadata y messages, o None si no existe
        """
        if session_id not in self._store or session_id not in self._metadata:
            return None
        
        metadata = self._metadata[session_id]
        messages = self._store[session_id].messages
        
        # Formatear mensajes para frontend
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                "content": msg.content
            })
        
        return {
            "session_id": session_id,
            "user_id": metadata.user_id,
            "title": metadata.title,
            "created_at": metadata.created_at.isoformat(),
            "updated_at": metadata.updated_at.isoformat(),
            "message_count": metadata.message_count,
            "expediente_number": metadata.expediente_number,
            "messages": formatted_messages
        }
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        Elimina una sesión y sus metadatos.
        
        Args:
            session_id: ID de la sesión
            user_id: ID del usuario (para validación)
            
        Returns:
            True si se eliminó, False si no existía
        """
        # Validar que la sesión pertenece al usuario
        if (user_id in self._user_sessions and 
            session_id in self._user_sessions[user_id]):
            
            # Eliminar del store
            if session_id in self._store:
                del self._store[session_id]
            
            # Eliminar metadatos
            if session_id in self._metadata:
                del self._metadata[session_id]
            
            # Eliminar del índice de usuario
            self._user_sessions[user_id].remove(session_id)
            
            logger.info(f"Sesión {session_id} eliminada para usuario {user_id}")
            return True
        
        logger.warning(f"Intento de eliminar sesión {session_id} falló (usuario: {user_id})")
        return False
    
    def clear_user_sessions(self, user_id: str):
        """
        Elimina todas las sesiones de un usuario.
        
        Args:
            user_id: ID del usuario
        """
        session_ids = self._user_sessions.get(user_id, []).copy()
        
        for session_id in session_ids:
            self.delete_session(session_id, user_id)
        
        logger.info(f"Todas las sesiones de {user_id} eliminadas ({len(session_ids)} sesiones)")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del store para debugging"""
        return {
            "total_sessions": len(self._store),
            "total_users": len(self._user_sessions),
            "total_messages": sum(
                len(history.messages) 
                for history in self._store.values()
            )
        }


# Instancia global del store
conversation_store = ConversationStore()


def get_session_history_func() -> Callable:
    """
    Retorna la función para obtener historial de sesión.
    
    Esta función es compatible con RunnableWithMessageHistory:
    
    Usage:
        with_message_history = RunnableWithMessageHistory(
            chain,
            get_session_history_func(),
            input_messages_key="input",
            history_messages_key="chat_history",
        )
    
    Returns:
        Callable que acepta session_id y retorna BaseChatMessageHistory
    """
    return conversation_store.get_session_history
