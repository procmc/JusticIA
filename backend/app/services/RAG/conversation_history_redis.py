"""
Servicio de persistencia de historial de conversaciones usando Redis.
No interfiere con el manejo de contexto en memoria de session_store.py

Este módulo maneja SOLO la persistencia del historial:
- Guardar conversaciones completas en Redis
- Cargar conversaciones desde Redis
- Listar conversaciones por usuario
- Eliminar conversaciones

El contexto activo en memoria sigue siendo manejado por session_store.py
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import redis
from app.config.config import REDIS_URL

logger = logging.getLogger(__name__)


class RedisConversationHistory:
    """
    Servicio de persistencia de historial en Redis.
    Complementa (no reemplaza) el session_store para manejo de contexto.
    """
    
    def __init__(self, redis_url: str = REDIS_URL):
        """
        Inicializa conexión a Redis.
        
        Args:
            redis_url: URL de conexión a Redis (ej: redis://localhost:6379)
        """
        try:
            # Parsear URL de Redis
            if redis_url.startswith('redis://'):
                redis_url = redis_url.replace('redis://', '')
            
            host_port = redis_url.split(':')
            host = host_port[0]
            port = int(host_port[1].split('/')[0]) if len(host_port) > 1 else 6379
            db = int(host_port[1].split('/')[1]) if '/' in redis_url else 2  # DB 2 para conversaciones
            
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,  # Usar DB diferente a Celery (0 y 1)
                decode_responses=True,  # Decodificar automáticamente a strings
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # Verificar conexión
            self.redis_client.ping()
            logger.info(f"✅ RedisConversationHistory conectado a {host}:{port}/DB{db}")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}", exc_info=True)
            raise
    
    # ============================================
    # CLAVES DE REDIS
    # ============================================
    
    def _conversation_key(self, session_id: str) -> str:
        """Clave para datos completos de conversación"""
        return f"conversation:{session_id}"
    
    def _user_index_key(self, user_id: str) -> str:
        """Clave para índice de sesiones por usuario"""
        return f"user_sessions:{user_id}"
    
    def _metadata_key(self, session_id: str) -> str:
        """Clave para metadatos de conversación (lista rápida)"""
        return f"conversation_meta:{session_id}"
    
    # ============================================
    # OPERACIONES PRINCIPALES
    # ============================================
    
    def save_conversation(
        self,
        session_id: str,
        user_id: str,
        messages: List[Dict],
        metadata: Dict
    ) -> bool:
        """
        Guarda una conversación completa en Redis.
        
        Args:
            session_id: ID de la sesión
            user_id: ID del usuario
            messages: Lista de mensajes [{type, content, timestamp}, ...]
            metadata: Metadatos (title, created_at, updated_at, etc.)
        
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Preparar datos completos
            conversation_data = {
                "metadata": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "created_at": metadata.get("created_at", datetime.utcnow().isoformat()),
                    "updated_at": datetime.utcnow().isoformat(),
                    "title": metadata.get("title", "Nueva conversación"),
                    "message_count": len(messages),
                    "expediente_number": metadata.get("expediente_number")
                },
                "messages": messages
            }
            
            # 1. Guardar conversación completa
            conv_key = self._conversation_key(session_id)
            self.redis_client.set(
                conv_key,
                json.dumps(conversation_data, ensure_ascii=False),
                ex=60 * 60 * 24 * 30  # TTL: 30 días
            )
            
            # 2. Guardar metadatos separados (para listado rápido)
            meta_key = self._metadata_key(session_id)
            self.redis_client.set(
                meta_key,
                json.dumps(conversation_data["metadata"], ensure_ascii=False),
                ex=60 * 60 * 24 * 30
            )
            
            # 3. Agregar a índice de usuario (sorted set por timestamp)
            user_index = self._user_index_key(user_id)
            timestamp = datetime.fromisoformat(
                conversation_data["metadata"]["updated_at"]
            ).timestamp()
            
            self.redis_client.zadd(
                user_index,
                {session_id: timestamp}
            )
            
            # TTL para índice de usuario
            self.redis_client.expire(user_index, 60 * 60 * 24 * 30)
            
            logger.info(f"✅ Conversación {session_id} guardada en Redis ({len(messages)} mensajes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando conversación {session_id} en Redis: {e}", exc_info=True)
            return False
    
    def load_conversation(self, session_id: str) -> Optional[Dict]:
        """
        Carga una conversación completa desde Redis.
        
        Args:
            session_id: ID de la sesión
        
        Returns:
            Dict con metadata y messages, o None si no existe
        """
        try:
            conv_key = self._conversation_key(session_id)
            data = self.redis_client.get(conv_key)
            
            if data:
                conversation = json.loads(data)
                logger.info(f"✅ Conversación {session_id} cargada desde Redis")
                return conversation
            
            logger.debug(f"Conversación {session_id} no encontrada en Redis")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error cargando conversación {session_id} desde Redis: {e}", exc_info=True)
            return None
    
    def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """
        Obtiene lista de conversaciones de un usuario (solo metadatos).
        
        Args:
            user_id: ID del usuario
            limit: Máximo de conversaciones a retornar
        
        Returns:
            Lista de metadatos ordenados por updated_at (más reciente primero)
        """
        try:
            user_index = self._user_index_key(user_id)
            
            # Obtener session_ids ordenados por timestamp (más reciente primero)
            session_ids = self.redis_client.zrevrange(user_index, 0, limit - 1)
            
            if not session_ids:
                logger.info(f"Usuario {user_id} no tiene conversaciones en Redis")
                return []
            
            # Cargar metadatos de cada conversación
            conversations = []
            for session_id in session_ids:
                meta_key = self._metadata_key(session_id)
                meta_data = self.redis_client.get(meta_key)
                
                if meta_data:
                    metadata = json.loads(meta_data)
                    conversations.append(metadata)
            
            logger.info(f"✅ Usuario {user_id} tiene {len(conversations)} conversaciones en Redis")
            return conversations
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo conversaciones de usuario {user_id}: {e}", exc_info=True)
            return []
    
    def delete_conversation(self, session_id: str, user_id: str) -> bool:
        """
        Elimina una conversación de Redis.
        
        Args:
            session_id: ID de la sesión a eliminar
            user_id: ID del usuario (para validación)
        
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            # 1. Verificar que la conversación pertenece al usuario
            conversation = self.load_conversation(session_id)
            
            if not conversation:
                logger.warning(f"Conversación {session_id} no existe en Redis")
                return False
            
            if conversation["metadata"]["user_id"] != user_id:
                logger.warning(f"Usuario {user_id} no puede eliminar conversación {session_id}")
                return False
            
            # 2. Eliminar conversación completa
            conv_key = self._conversation_key(session_id)
            self.redis_client.delete(conv_key)
            
            # 3. Eliminar metadatos
            meta_key = self._metadata_key(session_id)
            self.redis_client.delete(meta_key)
            
            # 4. Eliminar del índice de usuario
            user_index = self._user_index_key(user_id)
            self.redis_client.zrem(user_index, session_id)
            
            logger.info(f"✅ Conversación {session_id} eliminada de Redis")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error eliminando conversación {session_id}: {e}", exc_info=True)
            return False
    
    def get_stats(self) -> Dict:
        """
        Obtiene estadísticas del almacenamiento Redis.
        
        Returns:
            Dict con estadísticas de uso
        """
        try:
            # Contar claves por patrón
            conversation_keys = list(self.redis_client.scan_iter("conversation:*", count=1000))
            user_index_keys = list(self.redis_client.scan_iter("user_sessions:*", count=1000))
            
            # Info de memoria
            info = self.redis_client.info("memory")
            
            stats = {
                "total_conversations": len(conversation_keys),
                "total_users": len(user_index_keys),
                "redis_memory_used_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                "redis_db": self.redis_client.connection_pool.connection_kwargs.get("db", 2)
            }
            
            logger.info(f"📊 Redis Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo stats de Redis: {e}", exc_info=True)
            return {}
    
    def health_check(self) -> bool:
        """
        Verifica que Redis esté funcionando.
        
        Returns:
            bool: True si Redis responde
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"❌ Redis health check falló: {e}")
            return False


# ============================================
# INSTANCIA GLOBAL
# ============================================

redis_history = None

def get_redis_history() -> RedisConversationHistory:
    """
    Obtiene instancia singleton de RedisConversationHistory.
    Lazy initialization para evitar errores en entornos sin Redis.
    """
    global redis_history
    
    if redis_history is None:
        try:
            redis_history = RedisConversationHistory()
            logger.info("✅ RedisConversationHistory inicializado")
        except Exception as e:
            logger.error(f"❌ No se pudo inicializar RedisConversationHistory: {e}")
            raise
    
    return redis_history
