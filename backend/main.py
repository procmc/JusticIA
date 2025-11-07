import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.vectorstore.vectorstore import get_client
from app.routes import ingesta, usuarios, archivos, email, auth, similarity, rag, bitacora
from app.db import database
import asyncio
import logging
from app.utils.hf_model import ensure_model_available
from app.embeddings.embeddings import get_embeddings
from app.services.RAG.session_store import conversation_store

logger = logging.getLogger(__name__)

# Crear app sin lifespan primero
app = FastAPI(title="JusticIA API")


# Inicializar vectorstore en el evento startup
@app.on_event("startup")
async def startup_event():
    """Inicializar recursos al arranque"""
    # 1. Asegurar y cargar modelo de embeddings
    model_id = os.environ.get("EMBEDDING_MODEL")
    if model_id:
        ok = await asyncio.to_thread(ensure_model_available, model_id)
        if not ok:
            raise RuntimeError(f"No se pudo asegurar el modelo: {model_id}")
    
    # 2. Pre-cargar modelo en memoria (warm-up)
    try:
        embeddings = await get_embeddings()
        await embeddings.aembed_query("test")  # Inferencia de prueba
    except Exception as e:
        raise RuntimeError(f"Error cargando embeddings: {e}")
    
    # 3. Inicializar Milvus
    try:
        await get_client()
        print("Milvus configurado correctamente")
    except Exception as e:
        raise RuntimeError(f"Error inicializando Milvus: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al apagado"""
    try:
        # Guardar todas las conversaciones activas antes de cerrar
        logger.info("Guardando conversaciones antes de cerrar...")
        conversation_store.save_all_conversations()
        logger.info("Conversaciones guardadas exitosamente")
    except Exception as e:
        logger.error(f"Error guardando conversaciones al cerrar: {e}", exc_info=True)
    
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
app.include_router(bitacora.router, prefix="/bitacora", tags=["bitacora"])

# Servir archivos estáticos para avatares
uploads_path = Path("uploads")
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"message": "JusticIA API está funcionando", "version": "1.0.0"}
