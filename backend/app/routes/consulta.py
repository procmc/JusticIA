from fastapi import APIRouter, HTTPException
from app.schemas.schemas import ConsultaReq
from app.services.query_service import general_search
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class ConsultaGeneralRequest(BaseModel):
    query: str
    top_k: int = 30

class ConsultaGeneralResponse(BaseModel):
    respuesta: str
    documentos_encontrados: int
    sources: List[Dict[str, Any]]
    query_original: str

@router.post("/general", response_model=ConsultaGeneralResponse)
async def consulta_general(request: ConsultaGeneralRequest):
    """
    Endpoint para consulta general en toda la base de datos.
    Realiza búsqueda vectorial sin filtros y genera respuesta con LLM.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")
        
        resultado = await general_search(
            query=request.query,
            top_k=request.top_k
        )
        
        return ConsultaGeneralResponse(**resultado)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")
