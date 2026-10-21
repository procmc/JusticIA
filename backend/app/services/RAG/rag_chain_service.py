"""
Servicio coordinador del sistema RAG (Retrieval-Augmented Generation).

Este servicio es el punto de entrada principal para el asistente virtual JusticBot.
Coordina consultas generales y específicas de expedientes, gestiona el flujo de
streaming de respuestas y mantiene el contexto conversacional.

Arquitectura RAG:
    * Retriever: DynamicServIARetriever busca documentos relevantes en Qdrant
    * Chains: LangChain chains procesan contexto + historial + pregunta
    * LLM: Modelo de lenguaje genera respuestas basadas en documentos
    * Streaming: Server-Sent Events (SSE) para respuestas en tiempo real

Flujos soportados:
    1. Consulta general: Búsqueda semántica en toda la BD
    2. Consulta de expediente: Análisis profundo de un expediente específico
    3. Cambio de contexto: Actualización de expediente en sesión activa

Características:
    * Streaming SSE con detección de desconexión del cliente
    * Gestión automática de títulos de conversaciones
    * Validación de formato de expedientes
    * Fallback a general si expediente inválido
    * Límites configurables de documentos (top_k)

Example:
    >>> from app.services.rag.rag_chain_service import get_rag_service
    >>> rag_service = await get_rag_service()
    >>> 
    >>> # Consulta general
    >>> response = await rag_service.consulta_con_historial_streaming(
    ...     pregunta="¿Qué es la prescripción?",
    ...     session_id="session_user@example.com_1234567890",
    ...     top_k=15
    ... )
    >>> 
    >>> # Consulta de expediente específico
    >>> response = await rag_service.consulta_con_historial_streaming(
    ...     pregunta="¿Cuál es la sentencia?",
    ...     session_id="session_user@example.com_1234567890",
    ...     expediente_filter="24-000123-0001-PE"
    ... )

Note:
    * Singleton: Una instancia global compartida (get_rag_service)
    * Config centralizada: Parámetros en app.config.rag_config
    * top_k máximo: 15 documentos para evitar overflow de contexto
    * Formato expediente: YY-NNNNNN-NNNN-XX (validación con regex)

Ver también:
    * app.services.rag.retriever: Búsqueda vectorial
    * app.services.rag.general_chains: Chains conversacionales
    * app.services.rag.expediente_chains: Chains de expedientes
    * app.services.rag.session_store: Gestión de historial

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    2.0.0 - LangChain con streaming SSE
"""
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi import Request
import re
import logging
import json

from .retriever import DynamicServIARetriever
from .general_chains import create_conversational_rag_chain, stream_chain_response
from .expediente_chains import create_expediente_specific_chain
from .notebook_chains import create_notebook_specific_chain
from .prompts.notebook_prompt import reformular_referencia_imagen
from .session_store import conversation_store
from app.services.notebook_service import NotebookService, RecursoNoDisponible, forma_de_clave
from app.services.bitacora.notebooks_audit_service import (
    notebooks_audit_service, MOTIVO_NOTEBOOK_NO_DISPONIBLE, MOTIVO_CONVERSACION_NO_DISPONIBLE
)
from app.constants.tipos_accion import TiposAccion
from app.db.database import get_db

# Importar configuración centralizada
from app.config.rag_config import rag_config

logger = logging.getLogger(__name__)


class RAGChainService:
    """
    Servicio coordinador de consultas RAG.
    
    Maneja routing entre consultas generales y de expedientes,
    streaming de respuestas y gestión de contexto.
    
    Methods:
        consulta_con_historial_streaming: Consulta principal con routing automático
        update_expediente_context: Actualiza contexto de expediente en sesión
    """
    def __init__(self):
        self.notebook_service = NotebookService()

    async def _documentos_visibles(self, usuario_id: Optional[str]) -> set:
        """Los documentos que `usuario_id` puede ver, para que la búsqueda excluya lo ajeno (RF-17.3). Si la base falla,
        se falla cerrado: sin documentos visibles el chat no recibe ninguno, en vez de suponer que todos lo son."""
        db = next(get_db())
        try:
            return await self.notebook_service.ids_documentos_visibles(db, usuario_id)
        except Exception:
            logger.exception("No se pudieron calcular los documentos visibles; la búsqueda no devolverá documentos")
            return set()
        finally:
            db.close()

    async def _registrar_intento(self, usuario_id: Optional[str], tipo_accion_id: int, motivo: str) -> None:
        """Deja en la bitácora el intento de usar una conversación que no es del usuario, solo con su motivo (RF-21.32). Usa su
        propia sesión de base de datos; si el registro falla, la respuesta no cambia (RF-21)."""
        db = None
        try:
            db = next(get_db())
            await notebooks_audit_service.registrar_intento_fallido(
                db=db, usuario_id=usuario_id, tipo_accion_id=tipo_accion_id, motivo=motivo
            )
        except Exception as error:
            logger.warning(f"No se pudo registrar el intento fallido en la bitácora: {type(error).__name__}")
        finally:
            if db is not None:
                db.close()

    async def _conversacion_del_usuario(
        self, session_id: str, usuario_nombre: Optional[str], usuario_id: Optional[str], en_lista: bool
    ) -> tuple:
        """Decide qué conversación atiende el chat y devuelve `(identificador a usar, es_efimera)` (RNF-07.31, RNF-07.33).

        - Propia: la misma.
        - Inexistente: se crea con el usuario autenticado como dueño, aunque el identificador nombre a otro.
        - De otro usuario: se atiende como una conversación nueva (historial vacío) en una sesión efímera que no se guarda ni
          se lista, sin leer ni tocar la ajena, y se registra el intento fallido. Esto va antes de cualquier lectura o
          modificación de la conversación, incluida la fecha de su última actividad.
        Sin usuario autenticado (llamadas internas) no hay a quién comprobar: se conserva el comportamiento de siempre."""
        if usuario_nombre is None:
            return session_id, False
        propia = conversation_store.es_propia(session_id, usuario_nombre)
        if propia is False:
            await self._registrar_intento(usuario_id, TiposAccion.CONSULTA_RAG, MOTIVO_CONVERSACION_NO_DISPONIBLE)
            return conversation_store.crear_efimera(), True
        if propia is None:
            conversation_store.crear_conversacion(session_id, dueno=usuario_nombre, en_lista=en_lista)
        return session_id, False

    @staticmethod
    async def _descartando_la_efimera(flujo, session_id: str):
        """Entrega la respuesta tal cual y, al terminar (o al cortarse), descarta la conversación efímera."""
        try:
            async for trozo in flujo:
                yield trozo
        finally:
            conversation_store.descartar_efimera(session_id)

    async def _notebook_del_chat(self, notebook_id: str, usuario_id: Optional[str]):
        """El notebook propio que pide el chat de NotebookServIA. Si es ajeno, inexistente o no es un identificador numérico
        canónico lanza `RecursoNoDisponible` (RF-11.32): el llamador responde 404 uniforme sin llamar al modelo. Si la base
        falla, el error sube: sin poder comprobar el dueño no se contesta."""
        db = next(get_db())
        try:
            notebook = await self.notebook_service.obtener_notebook_para_chat(db, notebook_id, usuario_id)
        finally:
            db.close()
        if notebook is None:
            raise RecursoNoDisponible(MOTIVO_NOTEBOOK_NO_DISPONIBLE)
        return notebook

    # =====================================================================
    # LANGCHAIN ARCHITECTURE (Modern)
    # =====================================================================

    # Consulta principal
    async def consulta_con_historial_streaming(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        expediente_filter: Optional[str] = None,
        notebook_filter: Optional[str] = None,
        usuario_id: Optional[str] = None,
        http_request: Optional[Request] = None,
        usuario_nombre: Optional[str] = None,
        tema_es_clave: bool = False
    ):
        # `tema_es_clave`: la ruta ya comprobó con la base que el tema, sin tener forma de clave, se guardaría o igualaría como
        # la de un notebook (RF-17.34); el servicio no abre su propia sesión para ello.
        # 0. El notebook se comprueba ANTES de leer o modificar cualquier cosa, incluida la conversación (RF-11.32): uno
        # ajeno, inexistente o no numérico no cambia nada ni llega al modelo.
        notebook = None
        if notebook_filter is not None:
            notebook = await self._notebook_del_chat(notebook_filter, usuario_id)

        # 0b. De quién es la conversación, también ANTES de tocarla (RNF-07.31, RNF-07.33): la ajena se atiende como nueva.
        session_id, es_efimera = await self._conversacion_del_usuario(
            session_id, usuario_nombre, usuario_id, en_lista=notebook is None
        )
        try:
            respuesta = await self._despachar_consulta(
                pregunta, session_id, top_k, expediente_filter, notebook, usuario_id, http_request, tema_es_clave
            )
        except BaseException:
            if es_efimera:
                conversation_store.descartar_efimera(session_id)
            raise
        if es_efimera and hasattr(respuesta, "body_iterator"):
            respuesta.body_iterator = self._descartando_la_efimera(respuesta.body_iterator, session_id)
        elif es_efimera:
            conversation_store.descartar_efimera(session_id)
        return respuesta

    async def _despachar_consulta(
        self,
        pregunta: str,
        session_id: str,
        top_k: int,
        expediente_filter: Optional[str],
        notebook,
        usuario_id: Optional[str],
        http_request: Optional[Request],
        tema_es_clave: bool = False
    ):
        # 1. Actualizar la información de la conversación
        conversation_store.update_metadata(session_id)

        # 2. AQUÍ COORDINA: Decide qué flujo seguir
        if expediente_filter and (tema_es_clave or forma_de_clave(expediente_filter)):
            # Un tema con forma de clave de notebook (propia, ajena o inexistente) se trata como un tema inexistente: el
            # chat por tema nunca se acota a un notebook (solo el de NotebookServIA lo hace) y responde como el general,
            # que excluye lo ajeno (RF-11.31). La clave pedida no se registra en el servidor.
            logger.info("FLUJO: GENERAL CON HISTORIAL (tema con forma de clave de notebook)")
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k,
                usuario_id=usuario_id,
                http_request=http_request
            )
        elif expediente_filter and expediente_filter.strip():
            # → VA AL FLUJO DE EXPEDIENTE ESPECÍFICO
            logger.info("FLUJO: EXPEDIENTE ESPECÍFICO")
            return await self._consulta_expediente_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                expediente_numero=expediente_filter.strip(),
                usuario_id=usuario_id,
                http_request=http_request
            )
        elif notebook is not None:
            # → VA AL FLUJO DE NOTEBOOK ESPECÍFICO (NotebookServIA), con el notebook propio ya comprobado
            logger.info("FLUJO: NOTEBOOK ESPECÍFICO")
            return await self._consulta_notebook_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                notebook=notebook,
                usuario_id=usuario_id,
                http_request=http_request
            )
        else:
            logger.info(f"FLUJO: GENERAL CON HISTORIAL")
            # → VA AL FLUJO GENERAL
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k,
                usuario_id=usuario_id,
                http_request=http_request
            )
    
    # Consulta general con historial
    async def _consulta_general_con_historial(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        usuario_id: Optional[str] = None,
        http_request: Optional[Request] = None
    ):
        # Usar valor del config si no se especifica
        if top_k is None:
            top_k = rag_config.TOP_K_GENERAL
        
        # IMPORTANTE: Limitar top_k máximo para evitar sobrecarga del LLM
        # Con gpt-oss:20b (32K ctx), máximo recomendado es ~15 documentos
        MAX_TOP_K = 15
        if top_k > MAX_TOP_K:
            logger.warning(f"top_k={top_k} excede el máximo recomendado. Ajustando a {MAX_TOP_K}")
            top_k = MAX_TOP_K
        
        # Crear buscador con configuración centralizada; solo ve los documentos del usuario y los de temas generales (RF-17.3)
        retriever = DynamicServIARetriever(
            top_k=top_k,
            similarity_threshold=rag_config.SIMILARITY_THRESHOLD_GENERAL,
            documentos_visibles=await self._documentos_visibles(usuario_id)
        )
        
        # Crear chain conversacional
        chain = await create_conversational_rag_chain(
            retriever=retriever,
            with_history=True # "Recuerda la conversación anterior"
        )
        
        # Configuración de sesión
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        
        # Input para la chain
        input_dict = {
            "input": pregunta
        }
        
        # Streaming response
        async def event_generator():
            try:
                logger.info(f"Iniciando streaming para session: {session_id}")
                async for chunk in stream_chain_response(chain, input_dict, config, http_request):
                    yield chunk
                
                logger.info(f"Streaming finalizado para session: {session_id}")
                # Auto-generar título si es el primer mensaje
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                logger.error(f"Error en streaming con historial: {e}", exc_info=True)
                error_data = {
                    "type": "error",
                    "content": f"Error al procesar la consulta: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Consulta de expediente específico con historial
    async def _consulta_expediente_con_historial(
        self,
        pregunta: str,
        session_id: str,
        expediente_numero: str,
        usuario_id: Optional[str] = None,
        http_request: Optional[Request] = None
    ):
        logger.info(f"Expediente con historial - Número: {expediente_numero}")
        
        # Validar formato del expediente ingresado
        expediente_pattern = r'\b\d{2,4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"Formato inválido: {expediente_numero}")
            # Fallback a general
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=15,  # Usar valor por defecto
                usuario_id=usuario_id,
                http_request=http_request
            )
        
        # Actualizar la información de la conversación
        conversation_store.update_metadata(
            session_id=session_id,
            expediente_number=expediente_numero
        )
        
        # Crear retriever configurado para expediente específico con config centralizado
        retriever = DynamicServIARetriever(
            top_k=rag_config.TOP_K_EXPEDIENTE,
            similarity_threshold=rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE,
            expediente_filter=expediente_numero
        )
        
        logger.info(
            f"DynamicServIARetriever creado para expediente {expediente_numero} "
            f"(top_k: {rag_config.TOP_K_EXPEDIENTE}, "
            f"threshold: {rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE})"
        )
        
        # Crear chain especializada para expedientes
        chain = await create_expediente_specific_chain(
            retriever=retriever,
            expediente_numero=expediente_numero,
            with_history=True
        )
        
        logger.info(f"Chain expediente creada")
        
        # Configuración de sesión
        config = {
            "configurable": {
                "session_id": session_id
            }
        }
        
        # Input para la chain
        input_dict = {
            "input": pregunta
        }
        
        # Streaming response
        async def event_generator():
            try:
                logger.info(f"Iniciando streaming para expediente: {expediente_numero}, session: {session_id}")
                async for chunk in stream_chain_response(chain, input_dict, config, http_request):
                    yield chunk # Envía cada pedacito al frontend
                
                logger.info(f"Streaming finalizado para expediente: {expediente_numero}, session: {session_id}")
                # Cuando termina, genera título automático
                conversation_store.auto_generate_title(session_id)
                 
            except Exception as e:
                logger.error(f"Error en streaming expediente con historial: {e}", exc_info=True)
                # Si algo sale mal, envía error
                error_data = {
                    "type": "error",
                    "content": f"Error al procesar la consulta del expediente: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    
    # Consulta de notebook específico con historial (NotebookServIA)
    async def _consulta_notebook_con_historial(
        self,
        pregunta: str,
        session_id: str,
        notebook,
        usuario_id: Optional[str] = None,
        http_request: Optional[Request] = None
    ):
        """Chat acotado a un notebook propio. `notebook` ya fue comprobado como del usuario en `consulta_con_historial_streaming`
        (RF-11.32), que además actualizó la conversación: aquí no se vuelve a buscar ni a tocar nada."""
        logger.info("Notebook con historial")

        clave_interna = notebook.clave_interna  # ej. "NB-7" — clave de agrupación en Qdrant
        nombre_notebook = notebook.CT_Nombre

        # Reutiliza el mismo retriever/filtro híbrido de Qdrant que expediente
        # (expediente_filter es agnóstico al significado del string — Ciclo 3)
        retriever = DynamicServIARetriever(
            top_k=rag_config.TOP_K_EXPEDIENTE,
            similarity_threshold=rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE,
            expediente_filter=clave_interna,
            nombre_visible=nombre_notebook
        )

        logger.info(
            f"DynamicServIARetriever creado para notebook '{nombre_notebook}' ({clave_interna}) "
            f"(top_k: {rag_config.TOP_K_EXPEDIENTE}, "
            f"threshold: {rag_config.SIMILARITY_THRESHOLD_EXPEDIENTE})"
        )

        # Última vía contra el rechazo del modelo a reconocer imágenes
        # (5 refuerzos de prompt fallaron igual): reformular la pregunta
        # ANTES de que el modelo la vea, quitando la palabra "imagen"/
        # "foto" o el nombre del archivo. El historial de la conversación
        # guarda esta versión reformulada, no la que escribió el usuario
        # -- limitación conocida y aceptada de esta técnica.
        pregunta_para_llm = reformular_referencia_imagen(pregunta)
        if pregunta_para_llm != pregunta:
            logger.info(f"Pregunta reformulada para evitar el rechazo a imágenes: {pregunta!r} -> {pregunta_para_llm!r}")

        # Nombres reales de los archivos del notebook, para que el prompt
        # los liste explícitamente (ver get_notebook_system_prompt). Sin
        # esto, preguntas vagas ("el documento que subí", "el archivo
        # agregado") seguían negando el archivo aunque el contexto ya lo
        # tuviera. Consulta barata: es el mismo filtro por metadata que
        # ya usa la chain, no una búsqueda semántica nueva.
        # metadata usa 'nombre_archivo' en la práctica (aunque metadata_fields.py
        # documenta 'archivo' como canónico) — mismo fallback defensivo que ya
        # usa chunk_context_builder.py para esta misma inconsistencia.
        docs_del_notebook = await retriever._aget_relevant_documents(pregunta_para_llm)
        archivos_disponibles = [
            d.metadata.get('nombre_archivo') or d.metadata.get('archivo')
            for d in docs_del_notebook
            if d.metadata.get('nombre_archivo') or d.metadata.get('archivo')
        ]

        # Crear chain especializada para notebooks (prompt genérico, no judicial)
        chain = await create_notebook_specific_chain(
            retriever=retriever,
            nombre_notebook=nombre_notebook,
            with_history=True,
            pregunta=pregunta_para_llm,
            archivos_disponibles=archivos_disponibles
        )

        logger.info(f"Chain notebook creada")

        config = {
            "configurable": {
                "session_id": session_id
            }
        }

        input_dict = {
            "input": pregunta_para_llm
        }

        async def event_generator():
            try:
                logger.info(f"🚀 Iniciando streaming para notebook: {nombre_notebook}, session: {session_id}")
                async for chunk in stream_chain_response(chain, input_dict, config, http_request):
                    yield chunk

                logger.info(f"✅ Streaming finalizado para notebook: {nombre_notebook}, session: {session_id}")
                conversation_store.auto_generate_title(session_id)

            except Exception as e:
                logger.error(f"Error en streaming notebook con historial: {e}", exc_info=True)
                error_data = {
                    "type": "error",
                    "content": f"Error al procesar la consulta del notebook: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )

    # Actualizar contexto de expediente en la sesión
    async def update_expediente_context(
        self,
        session_id: str,
        expediente_number: str,
        action: str = "set",
        usuario_nombre: Optional[str] = None,
        usuario_id: Optional[str] = None
    ) -> bool:
        try:
            # El registro del servidor no lleva la conversación ni el tema pedidos: pueden ser de otra persona (RF-21.32)
            logger.info("Actualizando el tema de una conversación")

            # De quién es la conversación, antes de leerla, modificarla o añadirle mensajes (RNF-07.34): la de otro usuario se
            # trata igual que una inexistente (D9 A), sin tocarla ni crear nada, y se deja el intento fallido. Responde
            # «hecho»: la ruta arma su respuesta solo con lo que le pidieron, así que no se distingue de una inexistente.
            es_nueva = False
            if usuario_nombre is not None:
                propia = conversation_store.es_propia(session_id, usuario_nombre)
                if propia is False:
                    await self._registrar_intento(
                        usuario_id, TiposAccion.GESTIONAR_CONVERSACION, MOTIVO_CONVERSACION_NO_DISPONIBLE
                    )
                    return True
                es_nueva = propia is None

            # Actualizar metadatos de la sesión con el expediente
            conversation_store.update_metadata(
                session_id=session_id,
                expediente_number=expediente_number
            )

            # La conversación nueva se crea con el usuario autenticado como dueño (RNF-07.33)
            if es_nueva:
                conversation_store.crear_conversacion(session_id, dueno=usuario_nombre)

            # Obtener o crear el historial de la sesión
            session_history = conversation_store.get_session_history(session_id)

            # Crear mensaje del sistema para documentar el cambio
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

            if action == "change":
                # Mensaje indicando cambio de expediente
                user_message = HumanMessage(
                    content=f"Cambiar consulta a expediente: {expediente_number}"
                )
                assistant_message = AIMessage(
                    content=f"**Expediente cambiado:** {expediente_number}\n\nAhora puedes hacer cualquier consulta sobre este nuevo expediente. ¿Qué te gustaría saber?"
                )
            else:
                # Mensaje indicando establecimiento inicial del expediente
                user_message = HumanMessage(
                    content=f"Establecer consulta para expediente: {expediente_number}"
                )
                assistant_message = AIMessage(
                    content=f"**Expediente establecido:** {expediente_number}\n\nAhora puedes hacer cualquier consulta sobre este expediente. ¿Qué te gustaría saber?"
                )

            # Agregar mensajes al historial
            session_history.add_message(user_message)
            session_history.add_message(assistant_message)

            # Actualizar contador de mensajes en metadatos
            conversation_store.update_metadata(session_id)

            logger.info("Tema de la conversación actualizado")
            return True

        except Exception as e:
            logger.error(f"Error actualizando contexto de expediente: {e}", exc_info=True)
            return False

# Inicializar servicio RAG
_rag_service = None

# Obtener instancia singleton del servicio RAG
async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
