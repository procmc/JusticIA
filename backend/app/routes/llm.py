from fastapi import APIRouter
from pydantic import BaseModel
from app.llm.llm_service import consulta_simple, consulta_streaming
from app.llm.ollama_health import verificar_ollama

router = APIRouter()

class ConsultaLLM(BaseModel):
    pregunta: str

@router.get("/llm/health")
async def ollama_health_endpoint():
    """Verifica la conectividad con Ollama y lista modelos disponibles"""
    return await verificar_ollama()

@router.post("/llm/consulta")
async def consulta_llm_endpoint(req: ConsultaLLM):
    """Endpoint simple para consultas directas a Ollama"""
    print(f"Consulta recibida: {req.pregunta}")
    return await consulta_simple(req.pregunta)

@router.post("/llm/consulta-stream")
async def consulta_llm_stream_endpoint(req: ConsultaLLM):
    """Endpoint para consulta con streaming de respuesta"""
    print(f"Consulta recibida (stream): {req.pregunta}")
    return await consulta_streaming(req.pregunta)
