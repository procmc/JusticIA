from app.vectorstore.vectorstore import get_vectorstore
from fastapi import HTTPException
from app.config.config import COLLECTION_NAME

async def check_db_connection():
    try:
        vs = await get_vectorstore()
        # Si quieres mostrar la colección configurada:
        print(type(vs))
        print(dir(vs))
        return {"ok": True, "collections": vs.list_collections()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")
