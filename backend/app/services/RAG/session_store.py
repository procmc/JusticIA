from typing import Dict, List, Optional, Callable
from datetime import datetime
import pytz
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
import logging
from app.services.RAG.conversation_history_redis import get_redis_history
from app.config.rag_config import rag_config

logger = logging.getLogger(__name__)

# Zona horaria de Costa Rica
COSTA_RICA_TZ = pytz.timezone('America/Costa_Rica')

def get_costa_rica_now():
    """Obtiene la fecha y hora actual en zona horaria de Costa Rica"""
    return datetime.now(COSTA_RICA_TZ)


class InMemoryChatMessageHistory(BaseChatMessageHistory):
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


class LimitedChatMessageHistory(BaseChatMessageHistory):
    """
    Wrapper que limita los mensajes enviados al LLM pero mantiene el historial completo en Redis.
    
    - Redis guarda TODO sin límites (persistencia completa)
    - El LLM recibe solo los últimos N mensajes (optimización de contexto)
    - El frontend puede ver todo el historial sin restricciones
    """
    
    def __init__(self, full_history: InMemoryChatMessageHistory, limit: Optional[int] = None, save_callback: Optional[Callable] = None):
        """
        Args:
            full_history: Historial completo sin límites
            limit: Número máximo de mensajes a enviar al LLM (usa rag_config.CHAT_HISTORY_LIMIT si es None)
            save_callback: Función a llamar después de añadir mensajes para persistir en Redis
        """
        self.full_history = full_history
        self.limit = limit if limit is not None else rag_config.CHAT_HISTORY_LIMIT
        self.save_callback = save_callback
    
    @property
    def messages(self) -> List[BaseMessage]:
        """
        Devuelve solo los últimos N mensajes para el LLM.
        Esta propiedad es lo que LangChain lee al construir el prompt.
        """
        all_messages = self.full_history.messages
        
        if len(all_messages) <= self.limit:
            return all_messages
        
        limited = all_messages[-self.limit:]
        logger.debug(
            f"Historial limitado: {len(all_messages)} mensajes totales, "
            f"enviando últimos {len(limited)} al LLM"
        )
        return limited
    
    def add_message(self, message: BaseMessage) -> None:
        """Guarda en el historial completo (sin límites) y persiste en Redis"""
        self.full_history.add_message(message)
        # Persistir en Redis después de cada mensaje
        if self.save_callback:
            self.save_callback(self.full_history.session_id)
    
    def clear(self) -> None:
        """Limpia el historial completo"""
        self.full_history.clear()


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
    def __init__(self):
        # Almacenamiento principal EN MEMORIA: {session_id: InMemoryChatMessageHistory}
        # Este maneja el CONTEXTO ACTIVO de las conversaciones
        self._store: Dict[str, InMemoryChatMessageHistory] = {}
        
        # Índice por usuario: {user_id: [session_ids]}
        self._user_sessions: Dict[str, List[str]] = {}
        
        # Metadatos: {session_id: ConversationMetadata}
        self._metadata: Dict[str, ConversationMetadata] = {}
        
        # Cliente Redis para persistencia de historial (OBLIGATORIO)
        try:
            self._redis_history = get_redis_history()
            logger.info("ConversationStore usando Redis para persistencia")
        except Exception as e:
            logger.error(f"Redis no disponible - El historial NO se guardará: {e}")
            raise RuntimeError(
                "Redis es obligatorio para el sistema de conversaciones. "
                "Verifica que Redis esté corriendo y REDIS_URL esté configurado."
            ) from e
        
        logger.info("ConversationStore inicializado")
        
        # Redis carga conversaciones bajo demanda (no al inicio)
        logger.info("Redis listo - conversaciones se cargarán bajo demanda")
    
    def _save_conversation_to_file(self, session_id: str):
        """
        Guarda una conversación en Redis.
        """
        try:
            if session_id not in self._store or session_id not in self._metadata:
                logger.warning(f"No se puede guardar sesión {session_id}: no existe en memoria")
                return
            
            metadata = self._metadata[session_id]
            messages = self._store[session_id].messages
            
            # Formatear mensajes para persistencia
            formatted_messages = []
            for msg in messages:
                msg_dict = {
                    "type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content,
                    "timestamp": get_costa_rica_now().isoformat()
                }
                formatted_messages.append(msg_dict)
            
            # Guardar en Redis
            success = self._redis_history.save_conversation(
                session_id=session_id,
                user_id=metadata.user_id,
                messages=formatted_messages,
                metadata=metadata.to_dict()
            )
            
            if success:
                logger.info(f"Conversación {session_id} guardada en Redis ({len(formatted_messages)} mensajes)")
            else:
                logger.error(f"Error guardando conversación {session_id} en Redis")
            
        except Exception as e:
            logger.error(f"Error guardando conversación {session_id}: {e}", exc_info=True)
    
    def _load_conversation_from_file(self, session_id: str) -> bool:
        try:
            # Cargar desde Redis
            conversation_data = self._redis_history.load_conversation(session_id)
            
            if not conversation_data:
                logger.debug(f"Conversación {session_id} no existe en Redis")
                return False
            
            messages_count = len(conversation_data.get("messages", []))
            logger.info(f"Conversación {session_id} cargada desde Redis ({messages_count} mensajes)")
            
            # RESTAURAR EN MEMORIA
            metadata_dict = conversation_data.get("metadata", {})
            metadata = ConversationMetadata(
                session_id=metadata_dict["session_id"],
                user_id=metadata_dict["user_id"],
                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                updated_at=datetime.fromisoformat(metadata_dict["updated_at"]),
                title=metadata_dict.get("title", "Nueva conversación"),
                message_count=metadata_dict.get("message_count", 0),
                expediente_number=metadata_dict.get("expediente_number")
            )
            
            self._metadata[session_id] = metadata
            
            # Agregar al índice de usuario
            user_id = metadata.user_id
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            
            if session_id not in self._user_sessions[user_id]:
                self._user_sessions[user_id].append(session_id)
            
            # Restaurar mensajes EN MEMORIA
            history = InMemoryChatMessageHistory(session_id)
            for msg_dict in conversation_data.get("messages", []):
                msg_type = msg_dict.get("type")
                content = msg_dict.get("content")
                
                if msg_type == "human":
                    history.add_message(HumanMessage(content=content))
                elif msg_type == "ai":
                    history.add_message(AIMessage(content=content))
            
            self._store[session_id] = history
            
            logger.info(f"Conversación {session_id} restaurada en memoria ({len(history.messages)} mensajes)")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando conversación {session_id}: {e}", exc_info=True)
            return False
    
    def _load_all_conversations(self):
        logger.info("Redis configurado - conversaciones se cargarán bajo demanda")
    
    def save_all_conversations(self):
        """Guarda todas las conversaciones activas en archivos"""
        try:
            logger.info(f"Guardando {len(self._store)} conversaciones...")
            
            for session_id in self._store.keys():
                self._save_conversation_to_file(session_id)
            
            logger.info("Todas las conversaciones guardadas exitosamente")
            
        except Exception as e:
            logger.error(f"Error guardando todas las conversaciones: {e}", exc_info=True)
    
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """
        Obtiene el historial de una sesión, limitado para el LLM.
        
        - Guarda TODO en memoria y Redis (sin límites)
        - Retorna versión limitada que el LLM consume
        - Límite configurable en rag_config.CHAT_HISTORY_LIMIT
        """
        if session_id not in self._store:
            logger.info(f"Sesión {session_id} no está en memoria - intentando cargar...")
            # Intentar cargar desde Redis antes de crear una nueva
            if not self._load_conversation_from_file(session_id):
                logger.info(f"Creando nueva sesión: {session_id}")
                self._store[session_id] = InMemoryChatMessageHistory(session_id)
                
                # Crear metadatos si no existen
                if session_id not in self._metadata:
                    # Extraer user_id del session_id (formato: session_user@example.com_timestamp)
                    parts = session_id.split('_')
                    user_id = parts[1] if len(parts) >= 3 else 'unknown'
                    
                    self._create_metadata(session_id, user_id)
            else:
                logger.info(f"Historial cargado desde Redis: {session_id}")
        
        # Log del historial disponible
        full_history = self._store[session_id]
        total_messages = len(full_history.messages)
        logger.info(f"Historial para sesión {session_id}: {total_messages} mensajes en total")
        
        # Retornar versión limitada para el LLM (usa límite de rag_config)
        # IMPORTANTE: Pasar callback para guardar en Redis después de cada mensaje
        limited = LimitedChatMessageHistory(
            full_history,
            save_callback=self._save_conversation_to_file
        )
        logger.info(f"Enviando al LLM: {len(limited.messages)} mensajes (límite: {limited.limit})")
        return limited
    
    def _create_metadata(self, session_id: str, user_id: str) -> ConversationMetadata:
        """Crea metadatos para una nueva sesión"""
        now = get_costa_rica_now()
        
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
            metadata.updated_at = get_costa_rica_now()
            
            if title:
                metadata.title = title
            
            if expediente_number:
                metadata.expediente_number = expediente_number
            
            # Actualizar contador de mensajes
            if session_id in self._store:
                metadata.message_count = len(self._store[session_id].messages)
            
            # Guardar cambios en archivo
            self._save_conversation_to_file(session_id)
    
    def auto_generate_title(self, session_id: str):
        """Auto-genera título basado en el primer mensaje del usuario"""
        if session_id not in self._store or session_id not in self._metadata:
            return
        
        messages = self._store[session_id].messages
        
        # Buscar el primer mensaje del usuario
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if content.strip():
                    # Usar los primeros 60 caracteres
                    title = content.strip()[:60]
                    if len(content) > 60:
                        title += "..."
                    
                    self._metadata[session_id].title = title
                    logger.info(f"Título auto-generado para {session_id}: {title}")
                    
                    # Guardar cambios
                    self._save_conversation_to_file(session_id)
                    break
    
    def get_user_sessions(self, user_id: str) -> List[ConversationMetadata]:
        """
        Obtiene lista de conversaciones de un usuario desde Redis.
        """
        try:
            redis_conversations = self._redis_history.get_user_conversations(user_id)
            
            # Convertir de dict a ConversationMetadata
            conversations = []
            for conv_dict in redis_conversations:
                metadata = ConversationMetadata(
                    session_id=conv_dict["session_id"],
                    user_id=conv_dict["user_id"],
                    created_at=datetime.fromisoformat(conv_dict["created_at"]),
                    updated_at=datetime.fromisoformat(conv_dict["updated_at"]),
                    title=conv_dict.get("title", "Nueva conversación"),
                    message_count=conv_dict.get("message_count", 0),
                    expediente_number=conv_dict.get("expediente_number")
                )
                conversations.append(metadata)
            
            logger.info(f"Usuario {user_id} tiene {len(conversations)} conversaciones")
            return conversations
            
        except Exception as e:
            logger.error(f"Error obteniendo conversaciones desde Redis: {e}", exc_info=True)
            return []
    
    def get_session_detail(self, session_id: str) -> Optional[Dict]:
        # Si no está en memoria, intentar cargar desde archivo
        if session_id not in self._store or session_id not in self._metadata:
            logger.info(f"Conversación {session_id} no está en memoria, intentando cargar desde archivo...")
            loaded = self._load_conversation_from_file(session_id)
            
            if not loaded:
                logger.warning(f"No se pudo cargar conversación {session_id}")
                return None
        
        # Ahora debería estar en memoria
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
        Elimina una sesión de Redis/JSON y memoria.
        Mantiene validación de permisos.
        """
        
        # Si la sesión no está en memoria, intentar cargarla primero
        if session_id not in self._metadata:
            logger.info(f"Sesión {session_id} no está en memoria, intentando cargar para validar...")
            self._load_conversation_from_file(session_id)
        
        # Validar que la sesión pertenece al usuario
        session_belongs_to_user = False
        
        if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
            session_belongs_to_user = True
        elif session_id in self._metadata and self._metadata[session_id].user_id == user_id:
            session_belongs_to_user = True
        
        if session_belongs_to_user:
            # 1. ELIMINAR DE REDIS
            try:
                redis_deleted = self._redis_history.delete_conversation(session_id, user_id)
                if redis_deleted:
                    logger.info(f"Conversación {session_id} eliminada de Redis")
            except Exception as e:
                logger.error(f"Error eliminando de Redis: {e}", exc_info=True)
            
            # 2. ELIMINAR DE MEMORIA
            if session_id in self._store:
                del self._store[session_id]
            
            if session_id in self._metadata:
                del self._metadata[session_id]
            
            if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
                self._user_sessions[user_id].remove(session_id)
            
            logger.info(f"Sesión {session_id} eliminada completamente (usuario {user_id})")
            return True
        
        logger.warning(f"Intento de eliminar sesión {session_id} falló (usuario: {user_id})")
        return False
    
    def clear_user_sessions(self, user_id: str):
        session_ids = self._user_sessions.get(user_id, []).copy()
        
        for session_id in session_ids:
            self.delete_session(session_id, user_id)
        
        logger.info(f"Todas las sesiones de {user_id} eliminadas ({len(session_ids)} sesiones)")
    
    def get_stats(self) -> Dict:
        stats = {
            "memory_sessions": len(self._store),
            "memory_users": len(self._user_sessions),
            "memory_messages": sum(
                len(history.messages) 
                for history in self._store.values()
            ),
            "using_redis": True
        }
        
        # Agregar stats de Redis
        try:
            redis_stats = self._redis_history.get_stats()
            stats["redis"] = redis_stats
        except Exception as e:
            logger.error(f"Error obteniendo stats de Redis: {e}", exc_info=True)
            stats["redis_error"] = str(e)
        
        return stats

# Instancia global del store
conversation_store = ConversationStore()

def get_session_history_func() -> Callable:
    return conversation_store.get_session_history
