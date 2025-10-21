from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.services.RAG.rag_chain_service import get_rag_service
from app.services.RAG.session_store import conversation_store
from app.auth.jwt_auth import require_usuario_judicial
from app.db.database import get_db
from app.services.bitacora.rag_audit_service import rag_audit_service
import logging
import json
import time

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/rag", tags=["RAG - Consultas Inteligentes"])

class ConsultaConHistorialRequest(BaseModel):
    """Request para consultas con gestión de historial por session_id"""
    query: str
    session_id: str
    top_k: int = 15
    expediente_number: Optional[str] = None  # Opcional, para consultas de expediente específico


class UpdateExpedienteContextRequest(BaseModel):
    """Request para actualizar el contexto de expediente en una sesión"""
    session_id: str
    expediente_number: str
    action: str  # 'set' para establecer, 'change' para cambiar


@router.post("/consulta-con-historial-stream")
async def consulta_con_historial_stream(
    http_request: Request,
    request: ConsultaConHistorialRequest,
    rag_service=Depends(get_rag_service),
    current_user: dict = Depends(require_usuario_judicial),
    db: Session = Depends(get_db)
):
    start_time = time.time()

    try:
        # Validar entrada
        if not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="La consulta no puede estar vacía"
            )
        
        if not request.session_id.strip():
            raise HTTPException(
                status_code=400,
                detail="session_id es requerido"
            )
        
        # Usar query directamente (sin validación de seguridad por ahora)
        query_to_use = request.query
        
        logger.info(f"Consulta con historial - Session: {request.session_id}")
        logger.info(f"Query: {query_to_use[:100]}...")
        logger.info(f"Expediente: {request.expediente_number or 'None'}")
        logger.info(f"Usuario: {current_user.get('user_id', 'Unknown')} ({current_user.get('username', 'No email')})")
        
        # Llamar al nuevo método con gestión de historial (pasando http_request para detectar desconexión)
        response = await rag_service.consulta_con_historial_streaming(
            pregunta=query_to_use,
            session_id=request.session_id,
            top_k=min(request.top_k, 30),
            expediente_filter=request.expediente_number,
            http_request=http_request
        )
        
        # 🔥 AUDITORÍA: Registrar la consulta RAG exitosa
        end_time = time.time()
        tiempo_procesamiento = round(end_time - start_time, 2)
        
        # Determinar tipo de consulta
        tipo_consulta = "expediente" if request.expediente_number else "general"
        
        # Registrar en bitácora (async pero sin esperar para no afectar performance)
        try:
            await rag_audit_service.registrar_consulta_rag(
                db=db,
                usuario_id=current_user.get("user_id"),  # Usar cédula en lugar de email
                pregunta=request.query,
                session_id=request.session_id,
                tipo_consulta=tipo_consulta,
                expediente_numero=request.expediente_number,
                tiempo_procesamiento=tiempo_procesamiento
            )
        except Exception as audit_error:
            # Log error pero no fallar la consulta
            logger.warning(f"Error en auditoría RAG: {audit_error}")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en consulta con historial: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando consulta con historial: {str(e)}"
        )


@router.post("/update-expediente-context")
async def update_expediente_context(
    request: UpdateExpedienteContextRequest,
    rag_service=Depends(get_rag_service),
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Actualiza el contexto de expediente en una sesión sin hacer consulta.
    
    Esto permite que cuando el usuario cambia/establece un expediente,
    el backend actualice inmediatamente su historial con esta información,
    manteniendo la sincronización entre frontend y backend.
    
    Request Body:
    {
        "session_id": "session_user@example.com_1696425015000",
        "expediente_number": "2022-123456-7890-LA",
        "action": "set|change"
    }
    """
    try:
        # Validar entrada
        if not request.session_id.strip():
            raise HTTPException(
                status_code=400,
                detail="session_id es requerido"
            )
        
        if not request.expediente_number.strip():
            raise HTTPException(
                status_code=400,
                detail="expediente_number es requerido"
            )
        
        logger.info(f"Actualizando contexto expediente - Session: {request.session_id}")
        logger.info(f"Expediente: {request.expediente_number}, Acción: {request.action}")
        
        # Llamar al nuevo método para actualizar contexto
        success = await rag_service.update_expediente_context(
            session_id=request.session_id,
            expediente_number=request.expediente_number,
            action=request.action
        )
        
        if success:
            return {
                "success": True,
                "message": f"Contexto de expediente {request.expediente_number} actualizado correctamente",
                "session_id": request.session_id,
                "expediente_number": request.expediente_number,
                "action": request.action
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Error actualizando el contexto del expediente"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando contexto expediente: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando contexto del expediente: {str(e)}"
        )


# =====================================================================
# ENDPOINTS DE GESTIÓN DE HISTORIAL DE CONVERSACIONES
# =====================================================================

@router.get("/conversations")
async def get_user_conversations(
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Obtiene todas las conversaciones del usuario autenticado.
    """
    try:
        # El username es el email del usuario en este sistema
        user_id = current_user.get("username")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar al usuario"
            )
        
        # Obtener conversaciones del usuario
        conversations = conversation_store.get_user_sessions(user_id)
        
        # Convertir a diccionarios para la respuesta
        conversations_list = [conv.to_dict() for conv in conversations]
        
        logger.info(f"Usuario {user_id} tiene {len(conversations_list)} conversaciones")
        
        return {
            "success": True,
            "user_id": user_id,
            "conversations": conversations_list,
            "total": len(conversations_list)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo conversaciones: {str(e)}"
        )


@router.get("/conversations/{session_id}")
async def get_conversation_detail(
    session_id: str,
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Obtiene los detalles completos de una conversación específica,
    incluyendo todos los mensajes.
    """
    try:
        # El username es el email del usuario en este sistema
        user_id = current_user.get("username")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar al usuario"
            )
        
        # Obtener detalles de la conversación
        conversation = conversation_store.get_session_detail(session_id)
        
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversación {session_id} no encontrada"
            )
        
        # Verificar que la conversación pertenece al usuario
        if conversation.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para acceder a esta conversación"
            )
        
        logger.info(f"Conversación {session_id} obtenida para usuario {user_id}")
        
        return {
            "success": True,
            "conversation": conversation
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo detalles de conversación: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo detalles de conversación: {str(e)}"
        )


@router.delete("/conversations/{session_id}")
async def delete_conversation(
    session_id: str,
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Elimina una conversación específica del usuario.
    Elimina tanto de memoria como del archivo en disco.
    """
    try:
        # El username es el email del usuario en este sistema
        user_id = current_user.get("username")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar al usuario"
            )
        
        # Eliminar conversación
        success = conversation_store.delete_session(session_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Conversación {session_id} no encontrada o no pertenece al usuario"
            )
        
        logger.info(f"Conversación {session_id} eliminada para usuario {user_id}")
        
        return {
            "success": True,
            "message": f"Conversación {session_id} eliminada exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando conversación: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando conversación: {str(e)}"
        )


@router.post("/conversations/{session_id}/restore")
async def restore_conversation(
    session_id: str,
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Restaura una conversación desde el archivo JSON.
    Útil si la conversación no está en memoria pero existe en disco.
    """
    try:
        # El username es el email del usuario en este sistema
        user_id = current_user.get("username")
        
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="No se pudo identificar al usuario"
            )
        
        # Intentar cargar la conversación
        success = conversation_store._load_conversation_from_file(session_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo restaurar la conversación {session_id}"
            )
        
        # Verificar que pertenece al usuario
        conversation = conversation_store.get_session_detail(session_id)
        if not conversation or conversation.get("user_id") != user_id:
            # Eliminar de memoria si no pertenece al usuario
            if session_id in conversation_store._store:
                del conversation_store._store[session_id]
            
            raise HTTPException(
                status_code=403,
                detail="No tienes permiso para restaurar esta conversación"
            )
        
        logger.info(f"Conversación {session_id} restaurada para usuario {user_id}")
        
        return {
            "success": True,
            "message": f"Conversación {session_id} restaurada exitosamente",
            "conversation": conversation
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restaurando conversación: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error restaurando conversación: {str(e)}"
        )


@router.get("/conversations-stats")
async def get_conversations_stats(
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Obtiene estadísticas generales del sistema de conversaciones.
    Incluye información de Redis si está disponible.
    Solo para debugging/monitoreo.
    """
    try:
        stats = conversation_store.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/health/redis")
async def redis_health_check(
    current_user: dict = Depends(require_usuario_judicial)
):
    """
    Verifica el estado de conexión a Redis.
    Útil para debugging y monitoreo.
    """
    try:
        from app.services.RAG.conversation_history_redis import get_redis_history
        
        redis_history = get_redis_history()
        is_healthy = redis_history.health_check()
        
        if is_healthy:
            stats = redis_history.get_stats()
            return {
                "success": True,
                "status": "connected",
                "message": "Redis está funcionando correctamente",
                "stats": stats
            }
        else:
            return {
                "success": False,
                "status": "disconnected",
                "message": "Redis no responde"
            }
    
    except Exception as e:
        logger.error(f"Error en health check de Redis: {e}", exc_info=True)
        return {
            "success": False,
            "status": "error",
            "message": f"Error verificando Redis: {str(e)}"
        }

