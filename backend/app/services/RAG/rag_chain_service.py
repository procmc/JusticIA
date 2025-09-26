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
        # Preparar consulta con contexto de conversación si existe
        query_with_context = f"{conversation_context}\n\n{pregunta.strip()}" if conversation_context else pregunta.strip()

        # Calcular parámetros de retrieval
        optimal_params = calculate_optimal_retrieval_params(len(query_with_context), context_importance="high")
        effective_top_k = min(optimal_params.get("top_k", top_k), top_k)

        retriever = JusticIARetriever(top_k=effective_top_k)
        docs = await retriever._aget_relevant_documents(query_with_context)

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
