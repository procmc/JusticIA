from fastapi import HTTPException
from app.vectorstore.vectorstore import get_vectorstore
from app.schemas.schemas import IngestaItem, IngestaBatch

async def ingesta(item: IngestaItem):
    vs = await get_vectorstore()
    try:
        await vs.add_texts(
            texts=[item.texto],
            metadatas=[{"doc_id": item.id, **(item.metadata or {})}],
        )
        return {"status": "ok", "ingested": 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def ingesta_lote(batch: IngestaBatch):
    if not batch.items:
        raise HTTPException(status_code=400, detail="batch.items vacío")
    vs = await get_vectorstore()
    try:
        await vs.add_texts(
            texts=[it.texto for it in batch.items],
            metadatas=[{"doc_id": it.id, **(it.metadata or {})} for it in batch.items],
        )
        return {"status": "ok", "ingested": len(batch.items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
