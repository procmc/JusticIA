from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.llm.llm_service import consulta_simple, consulta_streaming
from app.llm.ollama_health import verificar_ollama
from app.services.query_service import general_search, general_search_streaming
from app.services.RAG.rag_chain_service import get_rag_service
from typing import List, Dict, Any

router = APIRouter()

class ConsultaLLM(BaseModel):
    pregunta: str

class ConsultaGeneralRequest(BaseModel):
    query: str
    top_k: int = 30
    has_context: bool = False  # Para manejar contexto de conversación

class ConsultaGeneralResponse(BaseModel):
    respuesta: str
    documentos_encontrados: int
    sources: List[Dict[str, Any]]
    query_original: str

@router.get("/health")
async def ollama_health_endpoint():
    """Verifica la conectividad con Ollama y lista modelos disponibles"""
    return await verificar_ollama()

@router.post("/consulta")
async def consulta_llm_endpoint(req: ConsultaLLM):
    """Endpoint simple para consultas directas a Ollama"""
    print(f"Consulta recibida: {req.pregunta}")
    return await consulta_simple(req.pregunta)

@router.post("/consulta-stream")
async def consulta_llm_stream_endpoint(req: ConsultaLLM):
    """Endpoint para consulta con streaming de respuesta"""
    print(f"Consulta recibida (stream): {req.pregunta}")
    return await consulta_streaming(req.pregunta)

@router.post("/consulta-general", response_model=ConsultaGeneralResponse)
async def consulta_general_endpoint(request: ConsultaGeneralRequest):
    """
    Endpoint para consulta general con RAG optimizado usando LangChain.
    Migrado de query_service manual a RAGChainService para mejor rendimiento.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        print(f"Consulta general RAG optimizada: {request.query}")
        
        # Usar el servicio RAG optimizado con LangChain
        rag_service = await get_rag_service()
        resultado = await rag_service.consulta_general(
            pregunta=request.query,
            top_k=min(request.top_k, 8)  # Optimizado para modelos pequeños
        )
        
        # Adaptar formato de respuesta
        if "error" in resultado:
            raise HTTPException(status_code=500, detail=resultado["error"])
        
        return ConsultaGeneralResponse(
            respuesta=resultado["respuesta"],
            documentos_encontrados=resultado.get("total_documentos", 0),
            sources=resultado.get("fuentes", []),
            query_original=request.query
        )
    
    except Exception as e:
        print(f"Error en consulta general RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@router.post("/consulta-general-stream")
async def consulta_general_stream_endpoint(request: ConsultaGeneralRequest):
    """
    Endpoint para consulta general con RAG optimizado y streaming usando LangChain.
    Migrado de query_service manual a RAGChainService para mejor rendimiento y prompts optimizados.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        print(f"Consulta general RAG streaming optimizada: {request.query}")
        
        # Extraer contexto de conversación si está presente
        conversation_context = ""
        query_parts = request.query.split('\n\n')
        if len(query_parts) > 1 and request.has_context:
            conversation_context = query_parts[0]
            actual_query = query_parts[-1]
        else:
            actual_query = request.query
        
        # Usar el servicio RAG optimizado con streaming
        rag_service = await get_rag_service()
        return await rag_service.consulta_general_streaming(
            pregunta=actual_query,
            top_k=min(request.top_k, 6),  # Menos documentos para streaming más rápido con modelos pequeños
            conversation_context=conversation_context
        )
    
    except Exception as e:
        print(f"Error en consulta general RAG streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")
