from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.llm.llm_service import consulta_simple, consulta_streaming
from app.llm.ollama_health import verificar_ollama
from app.services.query_service import general_search, general_search_streaming
from typing import List, Dict, Any

router = APIRouter()

class ConsultaLLM(BaseModel):
    pregunta: str

class ConsultaGeneralRequest(BaseModel):
    query: str
    top_k: int = 30

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
    Endpoint para consulta general con RAG.
    Busca en toda la base de datos vectorial y genera respuesta con contexto.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        print(f"Consulta general recibida: {request.query}")
        resultado = await general_search(
            query=request.query,
            top_k=request.top_k
        )
        
        return ConsultaGeneralResponse(**resultado)
    
    except Exception as e:
        print(f"Error en consulta general: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")

@router.post("/consulta-general-stream")
async def consulta_general_stream_endpoint(request: ConsultaGeneralRequest):
    """
    Endpoint para consulta general con RAG y streaming.
    Busca en toda la base de datos vectorial y genera respuesta en tiempo real.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        print(f"Consulta general streaming recibida: {request.query}")
        return await general_search_streaming(
            query=request.query,
            top_k=request.top_k
        )
    
    except Exception as e:
        print(f"Error en consulta general streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")
