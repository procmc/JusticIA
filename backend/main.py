import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.vectorstore.vectorstore import get_client
from app.routes import ingesta, usuarios, archivos, email, auth, similarity, rag
from app.db import database
import asyncio
from app.utils.hf_model import ensure_model_available

# Crear app sin lifespan primero
app = FastAPI(title="JusticIA API")


# Inicializar vectorstore en el evento startup
@app.on_event("startup")
async def startup_event():
    """Inicializar recursos al arranque"""
    # Intentar asegurar el modelo de embeddings en background (no bloquea el arranque)
    model_id = os.environ.get("EMBEDDING_MODEL")
    if model_id:
        # Bloqueamos el arranque hasta que el modelo esté asegurado para evitar
        # que el servidor atienda peticiones sin embeddings disponibles.
        ok = await asyncio.to_thread(ensure_model_available, model_id)
        if not ok:
            # Lanzar excepción para que uvicorn muestre fallo en el arranque
            raise RuntimeError(
                f"No se pudo descargar/asegurar el modelo de embeddings: {model_id}"
            )
    try:
        await get_client()
        print("Milvus configurado correctamente")
    except Exception as e:
        print(f"Error inicializando Milvus: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al apagado"""
    print("Aplicación cerrando...")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingesta.router, prefix="/ingesta", tags=["ingesta"])
app.include_router(usuarios.router, prefix="/usuarios", tags=["usuarios"])
app.include_router(archivos.router, prefix="/archivos", tags=["archivos"])
app.include_router(email.router, prefix="/email", tags=["email"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(similarity.router, prefix="/similarity", tags=["similarity"])
app.include_router(rag.router, tags=["rag"])


@app.get("/")
async def root():
    return {"message": "JusticIA API está funcionando", "version": "1.0.0"}
