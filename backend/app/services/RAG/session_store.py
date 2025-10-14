from typing import Dict, List, Optional, Callable
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Directorio para guardar conversaciones
CONVERSATIONS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "conversations"
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


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
        # Almacenamiento principal: {session_id: InMemoryChatMessageHistory}
        self._store: Dict[str, InMemoryChatMessageHistory] = {}
        
        # Índice por usuario: {user_id: [session_ids]}
        self._user_sessions: Dict[str, List[str]] = {}
        
        # Metadatos: {session_id: ConversationMetadata}
        self._metadata: Dict[str, ConversationMetadata] = {}
        
        logger.info("ConversationStore inicializado")
        
        # Cargar conversaciones existentes al iniciar
        self._load_all_conversations()
    
    def _get_conversation_file_path(self, session_id: str) -> Path:
        """Obtiene la ruta del archivo JSON para una sesión"""
        return CONVERSATIONS_DIR / f"{session_id}.json"
    
    def _save_conversation_to_file(self, session_id: str):
        """Guarda una conversación en archivo JSON"""
        try:
            if session_id not in self._store or session_id not in self._metadata:
                logger.warning(f"No se puede guardar sesión {session_id}: no existe en memoria")
                return
            
            metadata = self._metadata[session_id]
            messages = self._store[session_id].messages
            
            # Formatear mensajes para JSON
            formatted_messages = []
            for msg in messages:
                msg_dict = {
                    "type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content,
                    "timestamp": datetime.utcnow().isoformat()
                }
                formatted_messages.append(msg_dict)
            
            # Estructura completa del archivo
            conversation_data = {
                "metadata": metadata.to_dict(),
                "messages": formatted_messages
            }
            
            # Guardar en archivo
            file_path = self._get_conversation_file_path(session_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Conversación {session_id} guardada en {file_path}")
            
        except Exception as e:
            logger.error(f"Error guardando conversación {session_id}: {e}", exc_info=True)
    
    def _load_conversation_from_file(self, session_id: str) -> bool:
        """Carga una conversación desde archivo JSON"""
        try:
            file_path = self._get_conversation_file_path(session_id)
            
            if not file_path.exists():
                logger.debug(f"Archivo de conversación no existe: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
            
            # Restaurar metadatos
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
            
            # Restaurar mensajes
            history = InMemoryChatMessageHistory(session_id)
            for msg_dict in conversation_data.get("messages", []):
                msg_type = msg_dict.get("type")
                content = msg_dict.get("content")
                
                if msg_type == "human":
                    history.add_message(HumanMessage(content=content))
                elif msg_type == "ai":
                    history.add_message(AIMessage(content=content))
            
            self._store[session_id] = history
            
            logger.info(f"Conversación {session_id} cargada desde archivo ({len(history.messages)} mensajes)")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando conversación {session_id}: {e}", exc_info=True)
            return False
    
    def _load_all_conversations(self):
        """Carga todas las conversaciones guardadas al iniciar"""
        try:
            if not CONVERSATIONS_DIR.exists():
                logger.info("Directorio de conversaciones no existe, creándolo...")
                CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
                return
            
            json_files = list(CONVERSATIONS_DIR.glob("*.json"))
            logger.info(f"Encontrados {len(json_files)} archivos de conversaciones")
            
            loaded_count = 0
            for file_path in json_files:
                session_id = file_path.stem  # Nombre sin extensión
                if self._load_conversation_from_file(session_id):
                    loaded_count += 1
            
            logger.info(f"Conversaciones cargadas exitosamente: {loaded_count}/{len(json_files)}")
            
        except Exception as e:
            logger.error(f"Error cargando conversaciones: {e}", exc_info=True)
    
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
        """Elimina una sesión tanto de memoria como del archivo"""
        
        # Si la sesión no está en memoria, intentar cargarla primero
        if session_id not in self._metadata:
            logger.info(f"Sesión {session_id} no está en memoria, intentando cargar para validar...")
            self._load_conversation_from_file(session_id)
        
        # Validar que la sesión pertenece al usuario
        # Verificar en índice de usuario o en metadatos
        session_belongs_to_user = False
        
        if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
            session_belongs_to_user = True
        elif session_id in self._metadata and self._metadata[session_id].user_id == user_id:
            session_belongs_to_user = True
        
        if session_belongs_to_user:
            # Eliminar archivo JSON
            try:
                file_path = self._get_conversation_file_path(session_id)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Archivo de conversación eliminado: {file_path}")
                else:
                    # Intentar con formato antiguo
                    alt_session_id = session_id.replace('@', '_at_')
                    alt_file_path = self._get_conversation_file_path(alt_session_id)
                    if alt_file_path.exists():
                        alt_file_path.unlink()
                        logger.info(f"Archivo de conversación (formato antiguo) eliminado: {alt_file_path}")
            except Exception as e:
                logger.error(f"Error eliminando archivo de conversación: {e}", exc_info=True)
            
            # Eliminar del store
            if session_id in self._store:
                del self._store[session_id]
            
            # Eliminar metadatos
            if session_id in self._metadata:
                del self._metadata[session_id]
            
            # Eliminar del índice de usuario
            if user_id in self._user_sessions and session_id in self._user_sessions[user_id]:
                self._user_sessions[user_id].remove(session_id)
            
            logger.info(f"Sesión {session_id} eliminada para usuario {user_id}")
            return True
        
        logger.warning(f"Intento de eliminar sesión {session_id} falló (usuario: {user_id})")
        return False
    
    def clear_user_sessions(self, user_id: str):
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
    return conversation_store.get_session_history
