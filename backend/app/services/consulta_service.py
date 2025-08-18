from fastapi import HTTPException
from typing import List, Tuple
from app.vectorstore.vectorstore import get_vectorstore
from app.schemas.schemas import ConsultaReq

async def consulta(req: ConsultaReq):
    vs = await get_vectorstore()
    try:
        results: List[Tuple] = await vs.similarity_search_with_score(req.query, k=req.k)
        return {
            "results": [
                {"texto": doc.page_content, "metadata": doc.metadata, "score": float(score)}
                for doc, score in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
