from typing import List, Dict, Any, Optional, Union
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from app.llm.llm_service import get_llm
from fastapi.responses import StreamingResponse
import logging

# Imports de módulos RAG separados
from .retriever import JusticIARetriever
from .prompt_builder import create_justicia_prompt
from .context_formatter import format_documents_context, extract_document_sources, extract_unique_expedientes

logger = logging.getLogger(__name__)


class RAGChainService:
    """Servicio principal de RAG Chain para JusticIA"""
    
    def __init__(self):
        self.retriever = None
        self.llm: Optional[ChatOllama] = None
        self.qa_chain = None
    
    async def _initialize_components(self):
        """Inicializa los componentes necesarios"""
        if not self.llm:
            self.llm = await get_llm()
    
    async def consulta_general_streaming(self, pregunta: str, top_k: int = 15, conversation_context: str = ""):
        """Consulta general con streaming usando RAG Chain optimizado"""
        try:
            # Decidir qué tipo de LLM usar según si hay contexto de conversación
            logger.info(f"🔍 RAG SERVICE - conversation_context recibido: '{conversation_context[:100]}...'" if conversation_context else "🔍 RAG SERVICE - conversation_context VACÍO")
            
            if conversation_context and conversation_context.strip():
                # Hay contexto de conversación - usar LLM con memoria
                await self._initialize_components()
                llm_to_use = self.llm
                logger.info("✅ Usando LLM con contexto de conversación mantenido")
            else:
                # No hay contexto - usar LLM fresco sin memoria
                from app.llm.llm_service import get_fresh_llm
                llm_to_use = await get_fresh_llm()
                logger.info("🆕 Usando LLM fresco sin contexto previo - Nueva instancia creada")
            
            # Preparar consulta con contexto si existe
            query_with_context = f"{conversation_context}\n\n{pregunta.strip()}" if conversation_context else pregunta.strip()
            
            # Crear retriever para búsqueda general con parámetros optimizados
            from .context_formatter import calculate_optimal_retrieval_params
            
            # Calcular parámetros óptimos basados en la consulta
            optimal_params = calculate_optimal_retrieval_params(
                len(query_with_context), 
                context_importance="high"  # Usar alta importancia para evitar alucinaciones
            )
            
            # Usar top_k optimizado
            effective_top_k = min(optimal_params["top_k"], top_k)
            retriever = JusticIARetriever(top_k=effective_top_k)
            
            # Obtener documentos relevantes
            docs = await retriever._aget_relevant_documents(query_with_context)
            
            if not docs:
                async def empty_generator():
                    import json
                    error_data = {
                        "type": "error",
                        "content": "No se encontró información relevante en la base de datos para responder tu consulta.",
                        "done": True
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                
                return StreamingResponse(
                    empty_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                        "X-Accel-Buffering": "no",
                    }
                )
            
            # Usar contexto EXTENDIDO que aprovecha chunks completos del módulo de ingesta
            from .context_formatter import format_documents_context_adaptive
            context = format_documents_context_adaptive(
                docs, 
                query=pregunta, 
                context_importance="high"
            )
            
            # Log de mejoras en contexto
            context_chars = len(context)
            logger.info(f"Contexto extendido generado: {context_chars:,} caracteres de {len(docs)} chunks (promedio: {context_chars//len(docs):,} chars/chunk)")
            
            # Crear prompt unificado
            prompt_text = create_justicia_prompt(
                pregunta=pregunta,
                context=context,
                conversation_context=conversation_context
            )

            # Función generadora para streaming
            async def event_generator():
                import json
                import asyncio
                
                try:
                    # Verificar que el LLM esté disponible
                    if llm_to_use is None:
                        raise Exception("LLM no inicializado correctamente")
                    
                    # Enviar metadatos de inicio
                    start_data = {
                        "type": "start",
                        "content": "",
                        "metadata": {
                            "query": pregunta,
                            "docs_found": len(docs)
                        },
                        "done": False
                    }
                    yield f"data: {json.dumps(start_data, ensure_ascii=False)}\n\n"
                        
                    chunk_count = 0
                    async for chunk in llm_to_use.astream(prompt_text):
                        if hasattr(chunk, 'content') and chunk.content:
                            content = str(chunk.content)
                            
                            # Solo enviar contenido no vacío
                            if content:
                                chunk_count += 1
                                chunk_data = {
                                    "type": "chunk",
                                    "content": content,
                                    "done": False
                                }
                                yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                                
                                # Pequeña pausa para renderizado suave
                                await asyncio.sleep(0.01)
                    
                    # Enviar señal de finalización
                    done_data = {
                        "type": "done",
                        "content": "",
                        "done": True
                    }
                    yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
                            
                    logger.info(f"Streaming completado con {chunk_count} chunks")
                            
                except Exception as e:
                    logger.error(f"Error durante streaming RAG: {e}")
                    error_data = {
                        "type": "error",
                        "content": f"Error: {str(e)}",
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
                    "X-Accel-Buffering": "no",
                }
            )
            
        except Exception as e:
            logger.error(f"Error en consulta general streaming RAG: {e}")
            
            async def error_generator():
                import json
                error_data = {
                    "type": "error",
                    "content": f"Error procesando consulta: {str(e)}",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                error_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "X-Accel-Buffering": "no",
                }
            )

    async def consulta_general(self, pregunta: str, top_k: int = 15) -> Dict[str, Any]:
        """Consulta general en todos los expedientes usando RAG Chain con contexto extendido"""
        try:
            await self._initialize_components()
            
            # Calcular parámetros óptimos
            from .context_formatter import calculate_optimal_retrieval_params
            optimal_params = calculate_optimal_retrieval_params(
                len(pregunta), 
                context_importance="high"
            )
            
            # Crear retriever para búsqueda general con parámetros optimizados
            effective_top_k = min(optimal_params["top_k"], top_k)
            retriever = JusticIARetriever(top_k=effective_top_k)
            
            # Obtener documentos relevantes
            docs = await retriever._aget_relevant_documents(pregunta)
            
            if not docs:
                return {
                    "respuesta": "No se encontró información relevante en la base de datos para responder tu consulta.",
                    "expedientes_consultados": 0,
                    "fuentes": []
                }
            
            # Usar contexto EXTENDIDO también para método sin streaming
            from .context_formatter import format_documents_context_adaptive
            context = format_documents_context_adaptive(
                docs, 
                query=pregunta, 
                context_importance="high"
            )
            
            # Log de mejoras en contexto (sin streaming)
            context_chars = len(context)
            logger.info(f"Contexto extendido generado (sin streaming): {context_chars:,} caracteres de {len(docs)} chunks")
            
            # Asegurar que el LLM esté inicializado
            if not self.llm:
                await self._initialize_components()
            
            # Crear prompt unificado
            prompt_text = create_justicia_prompt(
                pregunta=pregunta,
                context=context,
                conversation_context=""
            )
            
            # Ejecutar LLM directamente con verificación
            if self.llm is None:
                raise Exception("LLM no inicializado correctamente")
            
            respuesta_raw = await self.llm.ainvoke(prompt_text)
            respuesta = getattr(respuesta_raw, "content", str(respuesta_raw))
            
            # Preparar metadatos de respuesta usando módulos
            expedientes_unicos = extract_unique_expedientes(docs)
            
            fuentes = extract_document_sources(docs)
            
            return {
                "respuesta": respuesta,
                "expedientes_consultados": len(expedientes_unicos),
                "expedientes": expedientes_unicos,
                "fuentes": fuentes,
                "total_documentos": len(docs)
            }
            
        except Exception as e:
            logger.error(f"Error en consulta general RAG: {e}")
            return {
                "error": f"Error procesando consulta: {str(e)}",
                "respuesta": "Hubo un error al procesar tu consulta. Por favor intenta nuevamente."
            }


# Instancia global del servicio
_rag_service = None

async def get_rag_service() -> RAGChainService:
    """Dependency para obtener el servicio RAG"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service