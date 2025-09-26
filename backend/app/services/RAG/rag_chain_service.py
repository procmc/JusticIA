from typing import List, Dict, Any
from fastapi.responses import StreamingResponse

from .retriever import JusticIARetriever
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

    async def consulta_general_streaming(self, pregunta: str, top_k: int = 15, conversation_context: str = ""):
        # SEPARACIÓN CRÍTICA: Usar SOLO la pregunta actual para buscar en la BD
        # El contexto de conversación se usa únicamente para generar la respuesta
        search_query = pregunta.strip()
        
        print(f"🔍 BÚSQUEDA EN BD: '{search_query}' (sin contexto histórico)")
        print(f"📋 CONTEXTO HISTÓRICO: {'SÍ' if conversation_context else 'NO'} ({len(conversation_context)} chars)")

        # Calcular parámetros de retrieval basado en la pregunta actual
        optimal_params = calculate_optimal_retrieval_params(len(search_query), context_importance="high")
        effective_top_k = min(optimal_params.get("top_k", top_k), top_k)

        retriever = JusticIARetriever(top_k=effective_top_k)
        # USAR SOLO LA PREGUNTA ACTUAL PARA LA BÚSQUEDA VECTORIAL
        docs = await retriever._aget_relevant_documents(search_query)
        
        print(f"📄 DOCUMENTOS ENCONTRADOS: {len(docs)} documentos para '{search_query}'")
        if docs:
            for i, doc in enumerate(docs[:3]):  # Mostrar solo los primeros 3
                preview = doc.page_content[:100].replace('\n', ' ')
                print(f"   {i+1}. {preview}...")

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

_rag_service = None

async def get_rag_service() -> RAGChainService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGChainService()
    return _rag_service
