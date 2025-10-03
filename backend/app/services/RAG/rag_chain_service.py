from typing import List, Dict, Any
from fastapi.responses import StreamingResponse

from .retriever import DynamicJusticIARetriever
from .prompt_builder import create_justicia_prompt
from .context_formatter import (
    format_documents_context_adaptive,
    calculate_optimal_retrieval_params,
    extract_document_sources,
    extract_unique_expedientes,
)

from app.llm.llm_service import consulta_general_streaming as llm_consulta_streaming


class RAGChainService:
    "Servicio RAG que arma el prompt con contexto recuperado y delega el streaming al LLM."

    def __init__(self):
        self.retriever = None

    async def consulta_general_streaming(self, pregunta: str, top_k: int = 15, conversation_context: str = "", expediente_filter: str = ""):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"RAG Chain Service - Procesando consulta: '{pregunta}'")
        
        # Usar SOLO la pregunta actual para buscar en la BD
        # El contexto de conversación se usa únicamente para generar la respuesta
        search_query = pregunta.strip()

        # La lógica de referencias contextuales se maneja en el context_analyzer

        # Extraer expedientes de toda la sesión
        session_expedients = []
        if conversation_context:
            import re
            expediente_pattern = r'\b\d{4}-\d{6}-\d{4}-[A-Z]{2}\b'
            session_expedients = list(set(re.findall(expediente_pattern, conversation_context)))

        # Calcular parámetros de retrieval basado en la pregunta actual
        optimal_params = calculate_optimal_retrieval_params(len(search_query), context_importance="high")
        effective_top_k = min(optimal_params.get("top_k", top_k), top_k)

        # RETRIEVER DINÁMICO: Completamente adaptativo
        retriever = DynamicJusticIARetriever(
            top_k=effective_top_k, 
            conversation_context=conversation_context,
            session_expedients=session_expedients
        )
        

        
        # Si hay filtro de expediente, agregarlo a la consulta para que el retriever lo detecte
        if expediente_filter and expediente_filter.strip():
            search_query = f"Expediente {expediente_filter.strip()}: {search_query}"
        
        # Usar la pregunta (posiblemente con expediente) para la búsqueda vectorial
        docs = await retriever._aget_relevant_documents(search_query)

        if not docs:
            async def empty_generator():
                import json

                error_data = {"type": "error", "content": "No se encontró información relevante.", "done": True}
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

            return StreamingResponse(empty_generator(), media_type="text/event-stream")

        # Formatear contexto recuperado
        context = format_documents_context_adaptive(docs, query=pregunta, context_importance="high")

        # Crear prompt final que incluye pregunta, contexto recuperado y conversation_context
        prompt_text = create_justicia_prompt(pregunta=pregunta, context=context, conversation_context=conversation_context)

        # Delegar el streaming al módulo LLM (que debe devolver un StreamingResponse)
        return await llm_consulta_streaming(prompt_text)
    
    async def responder_solo_con_contexto(self, pregunta: str, conversation_context: str = ""):
        """
        Responde usando SOLO el contexto de conversación previo, sin buscar en la BD.
        Usado cuando se detecta que la pregunta se refiere exclusivamente al contexto previo.
        """
        
        if not conversation_context:
            async def no_context_generator():
                import json
                error_data = {
                    "type": "error", 
                    "content": "No hay contexto previo disponible para responder esta consulta.",
                    "done": True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(no_context_generator(), media_type="text/event-stream")
        
        # FILTRAR CONTEXTO POR TEMA MÁS RECIENTE
        filtered_context = self._filter_context_by_recent_topic(conversation_context, pregunta)
        
        # Crear prompt que usa SOLO el contexto de conversación
        prompt_context_only = f"""Eres JusticIA, un asistente especializado en derecho costarricense.

El usuario te está haciendo una pregunta sobre información que ya discutimos previamente en esta conversación.

HISTORIAL DE LA CONVERSACIÓN:
{filtered_context}

NUEVA PREGUNTA DEL USUARIO:
{pregunta}

INSTRUCCIONES CRÍTICAS:
- Responde ÚNICAMENTE basándote en la información del historial de conversación anterior
- IMPORTANTE: Si la pregunta se refiere a "el primer caso", "el segundo expediente", etc., identifica A QUÉ TEMA SE REFIERE:
  * Si la conversación cambió de tema recientemente, usa SOLO la información más RECIENTE del nuevo tema
  * Si pregunta por "el primer expediente" después de una consulta sobre comercial, se refiere al PRIMER expediente comercial mencionado
  * Si pregunta por "el último expediente" después de una consulta sobre narcotráfico, se refiere al ÚLTIMO expediente de narcotráfico
- Analiza el contexto para determinar cuál es el tema MÁS RECIENTE al que se refiere la pregunta
- NO mezcles información de diferentes temas de la conversación
- Si no tienes suficiente información en el historial, explica qué información específica te falta
- Mantén el tono profesional y preciso

Respuesta:"""
        
        # Usar el LLM solo con el contexto de conversación
        return await llm_consulta_streaming(prompt_context_only)
    
    def _filter_context_by_recent_topic(self, conversation_context: str, pregunta: str) -> str:
        """
        Filtra el contexto para mantener solo información relevante al tema más reciente.
        """
        # Detectar temas en la pregunta
        temas_pregunta = []
        if any(word in pregunta.lower() for word in ['comercial', 'mercantil', 'societario', 'empresa']):
            temas_pregunta.append('comercial')
        if any(word in pregunta.lower() for word in ['narcotráfico', 'drogas', 'penal', 'delito']):
            temas_pregunta.append('penal')
        
        # Si no se detecta tema específico en la pregunta, usar todo el contexto
        if not temas_pregunta:
            return conversation_context
        
        # Dividir el contexto en intercambios
        intercambios = conversation_context.split('[Intercambio')
        if len(intercambios) <= 1:
            return conversation_context
        
        # Buscar el intercambio más reciente que contenga el tema
        contexto_filtrado = ['HISTORIAL DE CONVERSACIÓN PREVIA:']
        
        # Recorrer los intercambios de más reciente a más antiguo
        for i in range(len(intercambios) - 1, 0, -1):  # Empezar desde el final
            intercambio = '[Intercambio' + intercambios[i]
            
            # Verificar si este intercambio contiene el tema de interés
            contiene_tema = False
            for tema in temas_pregunta:
                if tema == 'comercial' and any(word in intercambio.lower() for word in ['comercial', 'mercantil', 'cm']):
                    contiene_tema = True
                    break
                elif tema == 'penal' and any(word in intercambio.lower() for word in ['penal', 'narcotráfico', 'pn', 'drogas']):
                    contiene_tema = True
                    break
            
            if contiene_tema:
                contexto_filtrado.append(intercambio)
                break  # Solo tomar el más reciente del tema
        
        # Si no se encontró contexto específico del tema, usar todo
        if len(contexto_filtrado) == 1:
            return conversation_context
        
        return '\n'.join(contexto_filtrado) + '\n---\nNUEVA CONSULTA:'

_rag_service = None

async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
