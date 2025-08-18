from fastapi import APIRouter
from app.schemas.schemas import ConsultaReq
from app.services.consulta_service import consulta

router = APIRouter()

@router.post("/consulta")
async def consulta_endpoint(req: ConsultaReq):
    return await consulta(req)
