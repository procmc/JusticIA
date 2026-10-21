"""
Endpoints de Consultas RAG (Retrieval-Augmented Generation).

Este módulo expone los endpoints de la API para realizar consultas inteligentes
al asistente de IA usando RAG. Soporta consultas generales y específicas por
expediente, con historial de conversación persistido por sesión.

Endpoints principales:
    POST /rag/consulta-con-historial-stream: Consulta streaming con historial
    POST /rag/update-expediente-context: Actualiza contexto de expediente en sesión

Arquitectura RAG:
    1. Usuario envía pregunta con session_id
    2. Backend recupera historial de la sesión
    3. Búsqueda semántica en Qdrant (top_k documentos similares)
    4. Construcción de prompt con contexto + historial
    5. LLM genera respuesta (streaming)
    6. Respuesta se guarda en historial de sesión
    7. Auditoría en bitácora

Streaming:
    - Usa Server-Sent Events (SSE) para respuestas incrementales
    - Mejora UX al mostrar respuesta mientras se genera
    - Detecta desconexiones de cliente para cancelar procesamiento

Auditoría:
    - Registra todas las consultas en bitácora (T_Bitacora_acciones_RAG)
    - Incluye: usuario, pregunta, tipo (general/expediente), tiempo

Example:
    >>> # Cliente HTTP
    >>> response = requests.post('/rag/consulta-con-historial-stream', json={
    ...     'query': '¿Cuál es la sentencia del caso?',
    ...     'session_id': 'session_user@mail.com_1234567890',
    ...     'expediente_number': '00-001234-0567-PE',
    ...     'top_k': 15
    ... }, stream=True)
    >>> for line in response.iter_lines():
    ...     if line.startswith(b'data: '):
    ...         data = json.loads(line[6:])
    ...         print(data['content'], end='')

Note:
    - session_id identifica la conversación única del usuario
    - expediente_number es opcional (None = búsqueda general)
    - top_k limita la cantidad de documentos recuperados (max 30)
    - Requiere autenticación JWT (usuario judicial)
"""

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
from app.services.bitacora.notebooks_audit_service import (
    notebooks_audit_service, MOTIVO_NOTEBOOK_NO_DISPONIBLE, MOTIVO_CONVERSACION_NO_DISPONIBLE
)
from app.services.notebook_service import NotebookService, RecursoNoDisponible, NO_DISPONIBLE
from app.constants.tipos_accion import TiposAccion
import logging
import json
import time
import traceback

logger = logging.getLogger(__name__)


async def _registrar_intento_de_conversacion(db: Session, current_user: dict) -> None:
    """Deja en la bitácora el intento de ver, restaurar o eliminar una conversación ajena o inexistente, solo con su motivo y
    como error de acceso (RF-21.32). Si el registro falla, la respuesta no cambia."""
    try:
        await notebooks_audit_service.registrar_intento_fallido(
            db=db,
            usuario_id=current_user.get("user_id"),
            tipo_accion_id=TiposAccion.GESTIONAR_CONVERSACION,
            motivo=MOTIVO_CONVERSACION_NO_DISPONIBLE
        )
    except Exception as audit_error:
        logger.warning(f"Error en auditoría de conversaciones: {type(audit_error).__name__}")


router = APIRouter(prefix="/rag", tags=["RAG - Consultas Inteligentes"])

class ConsultaConHistorialRequest(BaseModel):
    """Request para consultas con gestión de historial por session_id"""
    query: str
    session_id: str
    top_k: int = 15
    expediente_number: Optional[str] = None  # Opcional, para consultas de expediente específico
    notebook_id: Optional[str] = None  # Opcional, para consultas acotadas a un notebook (NotebookServIA)


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
        
        # El registro del servidor no lleva la conversación, el tema ni el notebook pedidos: pueden ser de otra persona o una
        # clave que no es del usuario (RNF-07.24, RF-21.32).
        logger.info("Consulta con historial")
        logger.info(f"Query: {query_to_use[:100]}...")
        logger.info(f"Usuario: {current_user.get('user_id', 'Unknown')} ({current_user.get('username', 'No email')})")

        # Un tema con forma de clave de notebook se atiende como chat general (RF-11.31). Si la clave no es de un notebook del
        # usuario (ajena o inexistente: no se distinguen), además de la consulta se deja el intento fallido (RF-21.33).
        tema_pedido = (request.expediente_number or "").strip()
        # También lo es el que la base guardaría o igualaría como una clave aunque no tenga su forma (RF-17.34).
        con_forma_de_clave = await NotebookService().es_tema_de_clave(db, tema_pedido)
        clasificacion = None
        if con_forma_de_clave:
            try:
                clasificacion = await NotebookService().clasificar_clave(db, tema_pedido, current_user["user_id"])
            except Exception as clasificacion_error:
                logger.warning(f"No se pudo clasificar el tema para la bitácora: {type(clasificacion_error).__name__}")

        # Llamar al nuevo método con gestión de historial (pasando http_request para detectar desconexión)
        response = await rag_service.consulta_con_historial_streaming(
            pregunta=query_to_use,
            session_id=request.session_id,
            top_k=min(request.top_k, 30),
            expediente_filter=request.expediente_number,
            notebook_filter=request.notebook_id,
            usuario_id=current_user["user_id"],
            http_request=http_request,
            usuario_nombre=current_user.get("username"),
            tema_es_clave=con_forma_de_clave
        )

        # AUDITORÍA: Registrar la consulta RAG exitosa
        end_time = time.time()
        tiempo_procesamiento = round(end_time - start_time, 2)

        # Determinar tipo de consulta, con el mismo orden con que decide el servicio. La clave de un notebook en el tema es
        # una consulta general, sin la clave (RF-21.33); el chat de un notebook propio (ya comprobado por el servicio) se
        # registra con alcance de notebook y su clave como tema (RF-21.31).
        tema_registrable = None
        if con_forma_de_clave:
            tipo_consulta = "general"
        elif tema_pedido:
            tipo_consulta = "expediente"
            tema_registrable = request.expediente_number
        elif request.notebook_id is not None:
            tipo_consulta = "notebook"
            tema_registrable = f"NB-{request.notebook_id}"
        else:
            tipo_consulta = "general"
        
        # Registrar en bitácora (async pero sin esperar para no afectar performance)
        try:
            await rag_audit_service.registrar_consulta_rag(
                db=db,
                usuario_id=current_user.get("user_id"),  # Usar cédula en lugar de email
                pregunta=request.query,
                session_id=request.session_id,
                tipo_consulta=tipo_consulta,
                expediente_numero=tema_registrable,
                tiempo_procesamiento=tiempo_procesamiento
            )
            if clasificacion is not None and clasificacion.tipo == NO_DISPONIBLE:
                await notebooks_audit_service.registrar_intento_fallido(
                    db=db,
                    usuario_id=current_user.get("user_id"),
                    tipo_accion_id=TiposAccion.CONSULTA_RAG,
                    motivo=MOTIVO_NOTEBOOK_NO_DISPONIBLE
                )
        except Exception as audit_error:
            # Log error pero no fallar la consulta
            logger.warning(f"Error en auditoría RAG: {audit_error}")
        
        return response
    
    except HTTPException:
        raise
    except RecursoNoDisponible as no_disponible:
        # Notebook ajeno, inexistente o con un identificador no numérico (RF-11.32): el mismo 404 para todos, sin llamar al
        # modelo, y el intento fallido solo con su motivo (RF-21.32). Si el registro falla, la respuesta es la misma.
        try:
            await notebooks_audit_service.registrar_intento_fallido(
                db=db,
                usuario_id=current_user.get("user_id"),
                tipo_accion_id=TiposAccion.CONSULTA_RAG,
                motivo=no_disponible.motivo
            )
        except Exception as audit_error:
            logger.warning(f"Error en auditoría RAG: {type(audit_error).__name__}")
        raise HTTPException(status_code=404, detail="Notebook no encontrado")
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
        
        # El registro del servidor no lleva la conversación ni el tema pedidos: pueden ser de otra persona (RF-21.32)
        logger.info("Actualizando el tema de una conversación")

        # Llamar al nuevo método para actualizar contexto. Si la conversación es de otro usuario, el servicio no la toca, deja el
        # intento fallido y responde «hecho»: el cuerpo de abajo se arma solo con lo que llegó en la petición, así que es el
        # mismo que con una conversación inexistente (RNF-07.34).
        success = await rag_service.update_expediente_context(
            session_id=request.session_id,
            expediente_number=request.expediente_number,
            action=request.action,
            usuario_nombre=current_user.get("username"),
            usuario_id=current_user.get("user_id")
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
        # Sin el texto de la excepción ni en la respuesta ni en el registro: puede traer rutas internas o lo pedido. El registro
        # conserva el tipo del error y su traza (archivo y línea) para diagnosticarlo.
        logger.error(
            "Error actualizando el tema de la conversación (%s)\n%s",
            type(e).__name__, "".join(traceback.format_tb(e.__traceback__))
        )
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
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
    current_user: dict = Depends(require_usuario_judicial),
    db: Session = Depends(get_db)
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
        
        # El dueño se comprueba ANTES de leer la conversación (RNF-07.6): la de otro usuario y la inexistente dan el mismo 404
        # y el mismo intento fallido; el 403 de antes revelaba que la conversación existía.
        if conversation_store.es_propia(session_id, user_id) is not True:
            await _registrar_intento_de_conversacion(db, current_user)
            raise HTTPException(
                status_code=404,
                detail=f"Conversación {session_id} no encontrada"
            )

        # Obtener detalles de la conversación
        conversation = conversation_store.get_session_detail(session_id)

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"Conversación {session_id} no encontrada"
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
    current_user: dict = Depends(require_usuario_judicial),
    db: Session = Depends(get_db)
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
        
        # Eliminar conversación: la de otro usuario y la inexistente dan el mismo 404 y el mismo intento fallido (RNF-07.6)
        success = False
        if conversation_store.es_propia(session_id, user_id) is True:
            success = conversation_store.delete_session(session_id, user_id)
        else:
            await _registrar_intento_de_conversacion(db, current_user)

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
    current_user: dict = Depends(require_usuario_judicial),
    db: Session = Depends(get_db)
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
        
        # El dueño se comprueba ANTES de cargar nada (RNF-07.6): la de otro usuario y la inexistente dan el mismo 404 y el mismo
        # intento fallido, y la ajena no llega a cargarse en memoria ni un instante.
        if conversation_store.es_propia(session_id, user_id) is not True:
            await _registrar_intento_de_conversacion(db, current_user)
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo restaurar la conversación {session_id}"
            )

        # Intentar cargar la conversación
        success = conversation_store._load_conversation_from_file(session_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo restaurar la conversación {session_id}"
            )

        conversation = conversation_store.get_session_detail(session_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail=f"No se pudo restaurar la conversación {session_id}"
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

