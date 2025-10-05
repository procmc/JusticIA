from typing import List, Dict, Any, Optional
from fastapi.responses import StreamingResponse
import re
import logging
import json

from .retriever import DynamicJusticIARetriever
from .prompt_builder import create_justicia_prompt
from .context_formatter import (
    format_documents_context_adaptive,
    calculate_optimal_retrieval_params,
    extract_document_sources,
    extract_unique_expedientes,
)
from .langchain_chains import (
    create_conversational_rag_chain,
    create_expediente_specific_chain,
    stream_chain_response
)
from .session_store import conversation_store

from app.llm.llm_service import consulta_general_streaming as llm_consulta_streaming

logger = logging.getLogger(__name__)


class RAGChainService:
    """
    Servicio RAG con dos flujos optimizados:
    - Flujo General: Búsqueda semántica multi-expediente con referencias contextuales
    - Flujo Expediente: Recuperación completa de un expediente específico con chunks ordenados
    
    El método público consulta_general_streaming() decide automáticamente el flujo según expediente_filter.
    """

    def __init__(self):
        self.retriever = None

    async def consulta_general_streaming(self, pregunta: str, top_k: int = 15, conversation_context: str = "", expediente_filter: str = ""):
        """
        MÉTODO PRINCIPAL - Decide automáticamente el flujo según expediente_filter.
        
        Args:
            pregunta: Pregunta del usuario
            top_k: Número máximo de documentos (usado solo en flujo general)
            conversation_context: Historial de conversación formateado
            expediente_filter: Número de expediente específico (opcional)
        
        Returns:
            StreamingResponse con la respuesta del LLM
        """
        logger.info(f"RAG SERVICE - Nueva consulta: '{pregunta[:50]}...'")
        logger.info(f"RAG SERVICE - Parámetros: top_k={top_k}, context_len={len(conversation_context)}, expediente={expediente_filter or 'None'}")
        
        # DECISIÓN DE FLUJO AUTOMÁTICA
        if expediente_filter and expediente_filter.strip():
            logger.info(f"FLUJO → EXPEDIENTE ESPECÍFICO: {expediente_filter}")
            return await self._consulta_expediente_streaming(
                pregunta=pregunta,
                expediente_numero=expediente_filter.strip(),
                conversation_context=conversation_context
            )
        else:
            logger.info(f"FLUJO → GENERAL: Búsqueda semántica multi-expediente")
            return await self._consulta_general_streaming(
                pregunta=pregunta,
                top_k=top_k,
                conversation_context=conversation_context
            )

    async def _consulta_general_streaming(self, pregunta: str, top_k: int = 15, conversation_context: str = ""):
        """
        FLUJO GENERAL: Búsqueda semántica con resolución de referencias contextuales.
        
        Optimizaciones:
        - Usa solo la pregunta actual para búsqueda vectorial
        - Resuelve referencias como "último caso", "ese expediente"
        - Top-k adaptativo según longitud de consulta
        - Threshold 0.3 (más estricto)
        """
        logger.info(f"GENERAL - Pregunta: '{pregunta}'")
        logger.info(f"GENERAL - Contexto: {len(conversation_context)} chars")
        
        # SEPARACIÓN CRÍTICA: Usar SOLO la pregunta actual para búsqueda vectorial
        search_query = pregunta.strip()

        logger.info(f"BÚSQUEDA EN BD: '{search_query}' (sin contexto histórico)")
        logger.info(f"CONTEXTO HISTÓRICO: {'SÍ' if conversation_context else 'NO'} ({len(conversation_context)} chars)")

        # Crear retriever con parámetros optimizados
        self.retriever = DynamicJusticIARetriever(
            top_k=top_k,
            similarity_threshold=0.3
        )
        
        # Búsqueda vectorial
        docs = await self.retriever._aget_relevant_documents(search_query)
        
        logger.info(f"GENERAL - {len(docs)} documentos encontrados")
        if docs:
            for i, doc in enumerate(docs[:3]):  # Log primeros 3
                preview = doc.page_content[:100].replace('\n', ' ')
                logger.debug(f"   {i+1}. {preview}...")

        if not docs:
            logger.warning(f"GENERAL - Sin resultados para: '{pregunta}'")
            async def empty_generator():
                import json
                error_data = {
                    "type": "error", 
                    "content": "No se encontró información relevante para tu consulta.",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            return StreamingResponse(empty_generator(), media_type="text/event-stream")

        # Formateo adaptativo del contexto
        context = format_documents_context_adaptive(
            docs, 
            query=pregunta,
            context_importance="high"
        )

        # Prompt con historial
        prompt_text = create_justicia_prompt(
            pregunta=pregunta, 
            context=context, 
            conversation_context=conversation_context
        )

        # Streaming al LLM
        logger.info(f"GENERAL - Enviando prompt al LLM ({len(prompt_text)} chars)")
        return await llm_consulta_streaming(prompt_text)

    async def _consulta_expediente_streaming(self, pregunta: str, expediente_numero: str, conversation_context: str = ""):
        """
        FLUJO EXPEDIENTE: Recupera TODOS los documentos del expediente específico.
        
        Optimizaciones:
        - Obtiene documentos completos del expediente (hasta 100)
        - Formateo estructurado por chunks con orden secuencial
        - Threshold 0.1 (más permisivo)
        - Top-k: 50 en fallback
        - Instrucciones especiales en el prompt
        """
        logger.info(f"EXPEDIENTE - Número: {expediente_numero}")
        logger.info(f"EXPEDIENTE - Pregunta: '{pregunta}'")
        
        # Validar formato de expediente
        expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"EXPEDIENTE - Formato inválido: {expediente_numero}")
            logger.info(f"EXPEDIENTE - Fallback a búsqueda general")
            # Fallback a general
            return await self._consulta_general_streaming(
                pregunta=pregunta,
                top_k=15,
                conversation_context=conversation_context
            )
        
        try:
            from app.vectorstore.operations import get_expedient_documents, search_by_text
            
            # Obtener TODOS los documentos del expediente
            complete_docs = await get_expedient_documents(expediente_numero)
            
            if not complete_docs or len(complete_docs) == 0:
                logger.warning(f"EXPEDIENTE - No encontrado en BD: {expediente_numero}")
                logger.info(f"EXPEDIENTE - Intentando búsqueda semántica con filtro")
    
                # Fallback: búsqueda semántica con mención del expediente
                search_query = f"Expediente {expediente_numero}: {pregunta}"
                complete_docs = await search_by_text(
                    query_text=search_query,
                    top_k=50,  # Más documentos para expedientes
                    score_threshold=0.1  # Más permisivo
                )
                
                if not complete_docs:
                    logger.error(f"EXPEDIENTE - No se encontró en búsqueda semántica tampoco")
                    async def not_found_generator():
                        import json
                        error_data = {
                            "type": "error",
                            "content": f"No se encontró el expediente {expediente_numero} en la base de datos.",
                            "done": True
                        }
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    return StreamingResponse(not_found_generator(), media_type="text/event-stream")

            logger.info(f"EXPEDIENTE - {len(complete_docs)} documentos recuperados")

            # Formateo adaptativo del contexto (sin chunk_context_builder)
            context = format_documents_context_adaptive(
                complete_docs,
                query=pregunta,
                context_importance="high"
            )

            logger.info(f"EXPEDIENTE - Contexto formateado: {len(context)} chars")

            # Prompt con instrucciones especiales para expediente
            expediente_instruction = (
                f"ANÁLISIS DE EXPEDIENTE ESPECÍFICO: {expediente_numero}\n"
                f"Tienes acceso a {len(complete_docs)} documentos completos de este expediente.\n"
                f"Los documentos están organizados secuencialmente por tipo (demandas, resoluciones, audio transcrito).\n"
                f"Los chunks de cada documento están en orden cronológico.\n"
                f"Usa esta estructura para dar respuestas precisas y contextualizadas.\n"
                f"Si la pregunta solicita información específica, búscala exhaustivamente en todos los documentos."
            )
            
            # Crear prompt base
            prompt_text = create_justicia_prompt(
                pregunta=pregunta,
                context=context,
                conversation_context=conversation_context
            )
            
            # Agregar instrucción especial al inicio
            prompt_text = expediente_instruction + "\n\n" + prompt_text
            
            # Streaming al LLM
            logger.info(f"EXPEDIENTE - Enviando prompt al LLM ({len(prompt_text)} chars)")
            return await llm_consulta_streaming(prompt_text)
            
        except Exception as e:
            logger.error(f"EXPEDIENTE - Error inesperado: {e}", exc_info=True)
            # Fallback a general
            logger.info(f"EXPEDIENTE - Fallback a búsqueda general por error")
            return await self._consulta_general_streaming(
                pregunta=pregunta,
                top_k=15,
                conversation_context=conversation_context
            )
    
    async def responder_solo_con_contexto(self, pregunta: str, conversation_context: str = ""):
        """
        Responde usando SOLO el contexto de conversación previo, sin buscar en la BD.
        Útil para preguntas que se refieren exclusivamente al historial.
        """
        logger.info(f"📚 SOLO CONTEXTO - Pregunta: '{pregunta}'")
        logger.info(f"📚 SOLO CONTEXTO - Sin búsqueda en BD")
        
        if not conversation_context:
            logger.warning(f"⚠️ SOLO CONTEXTO - No hay contexto previo disponible")
            async def no_context_generator():
                import json
                error_data = {
                    "type": "error", 
                    "content": "No hay contexto previo disponible para responder esta consulta.",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            return StreamingResponse(no_context_generator(), media_type="text/event-stream")
        
        # Prompt que usa SOLO el historial
        prompt_context_only = f"""Eres JusticIA, un asistente especializado en derecho costarricense.

El usuario te está haciendo una pregunta sobre información que ya discutimos previamente en esta conversación.

HISTORIAL DE LA CONVERSACIÓN:
{conversation_context}

NUEVA PREGUNTA DEL USUARIO:
{pregunta}

INSTRUCCIONES:
- Responde ÚNICAMENTE basándote en la información del historial de conversación anterior
- NO busques información nueva ni inventes datos
- Si la pregunta se refiere a "el primer caso", "el segundo expediente", etc., identifica claramente a cuál te refieres
- Si no tienes suficiente información en el historial, explica qué información específica te falta
- Mantén el tono profesional y preciso

Respuesta:"""

        logger.info(f"✅ SOLO CONTEXTO - Prompt generado: {len(prompt_context_only)} chars")
        return await llm_consulta_streaming(prompt_context_only)
    
    # =====================================================================
    # NUEVOS MÉTODOS CON LANGCHAIN CHAINS (Session-based)
    # =====================================================================
    
    async def consulta_con_historial_streaming(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 15,
        expediente_filter: Optional[str] = None
    ):
        """
        NUEVO MÉTODO - Consulta RAG con gestión automática de historial conversacional.
        
        Usa LangChain chains con RunnableWithMessageHistory para:
        - Reformulación automática de preguntas con contexto histórico
        - Gestión de sesiones automática (sin enviar historial desde frontend)
        - Detección de referencias contextuales mejorada
        
        Args:
            pregunta: Pregunta del usuario (sin contexto histórico)
            session_id: ID de la sesión de conversación
            top_k: Número de documentos a recuperar
            expediente_filter: Número de expediente específico (opcional)
        
        Returns:
            StreamingResponse con la respuesta del LLM
        
        Flujo:
        1. Backend recupera historial automáticamente usando session_id
        2. LangChain reformula pregunta si hace referencia al historial
        3. Retriever busca documentos relevantes
        4. LLM genera respuesta con contexto histórico + documentos
        5. Backend guarda automáticamente user message + assistant message
        """
        logger.info(f"🆕 CONSULTA CON HISTORIAL - Pregunta: '{pregunta[:50]}...'")
        logger.info(f"🆕 SESSION_ID: {session_id}")
        logger.info(f"🆕 Parámetros: top_k={top_k}, expediente={expediente_filter or 'None'}")
        
        # Actualizar metadatos de la sesión
        conversation_store.update_metadata(session_id)
        
        # Decidir flujo según expediente
        if expediente_filter and expediente_filter.strip():
            logger.info(f"🆕 FLUJO → EXPEDIENTE ESPECÍFICO: {expediente_filter}")
            return await self._consulta_expediente_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                expediente_numero=expediente_filter.strip()
            )
        else:
            logger.info(f"🆕 FLUJO → GENERAL CON HISTORIAL")
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=top_k
            )
    
    async def _consulta_general_con_historial(
        self,
        pregunta: str,
        session_id: str,
        top_k: int = 50  # Aumentado para más contexto
    ):
        """
        Consulta general usando LangChain chains con historial automático.
        Usa SmartRetrieverRouter (V2) que decide automáticamente el modo.
        """
        print(f"\n{'='*80}")
        print(f"🔄 CONSULTA GENERAL CON HISTORIAL")
        print(f"   - Pregunta: '{pregunta}'")
        print(f"   - Session ID: {session_id}")
        print(f"   - Top-K: {top_k}")
        print(f"{'='*80}\n")
        
        logger.info(f"🔄 GENERAL CON HISTORIAL - Creando chain conversacional")
        logger.info(f"🔄 Top-K configurado: {top_k}")
        
        # Crear retriever con parámetros optimizados
        retriever = DynamicJusticIARetriever(
            top_k=top_k,
            similarity_threshold=0.3
        )
        
        logger.info(f"✅ DynamicJusticIARetriever creado")
        
        # Crear chain conversacional
        chain = await create_conversational_rag_chain(
            retriever=retriever,
            with_history=True
        )
        
        logger.info(f"✅ Chain conversacional creada")
        
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
                async for chunk in stream_chain_response(chain, input_dict, config):
                    yield chunk
                
                # Auto-generar título si es el primer mensaje
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                logger.error(f"❌ Error en streaming con historial: {e}", exc_info=True)
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
    
    async def _consulta_expediente_con_historial(
        self,
        pregunta: str,
        session_id: str,
        expediente_numero: str
    ):
        """
        Consulta de expediente específico usando LangChain chains con historial.
        """
        logger.info(f"📂 EXPEDIENTE CON HISTORIAL - Número: {expediente_numero}")
        
        # Validar formato
        expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
        if not re.match(expediente_pattern, expediente_numero):
            logger.error(f"❌ Formato inválido: {expediente_numero}")
            # Fallback a general
            return await self._consulta_general_con_historial(
                pregunta=pregunta,
                session_id=session_id,
                top_k=15
            )
        
        # Actualizar metadatos con número de expediente
        conversation_store.update_metadata(
            session_id=session_id,
            expediente_number=expediente_numero
        )
        
        # Crear retriever configurado para expediente específico
        retriever = DynamicJusticIARetriever(
            top_k=50,
            similarity_threshold=0.2,
            expediente_filter=expediente_numero
        )
        
        logger.info(f"✅ DynamicJusticIARetriever creado para expediente {expediente_numero}")
        
        # Crear chain especializada para expedientes
        chain = await create_expediente_specific_chain(
            retriever=retriever,
            expediente_numero=expediente_numero,
            with_history=True
        )
        
        logger.info(f"✅ Chain expediente creada")
        
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
                async for chunk in stream_chain_response(chain, input_dict, config):
                    yield chunk
                
                # Auto-generar título si es el primer mensaje
                conversation_store.auto_generate_title(session_id)
                
            except Exception as e:
                logger.error(f"❌ Error en streaming expediente con historial: {e}", exc_info=True)
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

_rag_service = None

async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
