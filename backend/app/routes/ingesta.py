from fastapi import APIRouter
from app.schemas.schemas import IngestaItem, IngestaBatch
from app.services.ingesta_serivece import ingesta, ingesta_lote

router = APIRouter()

@router.post("/ingesta")
async def ingesta_endpoint(item: IngestaItem):
    return await ingesta(item)

@router.post("/ingesta/lote")
async def ingesta_lote_endpoint(batch: IngestaBatch):
    return await ingesta_lote(batch)
