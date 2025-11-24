"""
Punto de entrada principal de la API de JusticIA.

Este módulo inicializa la aplicación FastAPI con todos sus componentes:
- Routers de endpoints REST
- Middleware de CORS
- Archivos estáticos (avatares)
- Inicialización de recursos (embeddings, Milvus, modelos)
- Eventos de ciclo de vida (startup/shutdown)

Arquitectura de la aplicación:
    * FastAPI como framework web asíncrono
    * SQLAlchemy para ORM con SQL Server
    * Milvus para búsqueda vectorial
    * Ollama LLM para generación de respuestas
    * Celery para tareas asíncronas
    * Redis para caché y broker

Routers incluidos:
    * /ingesta: Carga y procesamiento de documentos
    * /usuarios: Gestión de usuarios del sistema
    * /archivos: Operaciones sobre archivos y documentos
    * /email: Envío de correos (recuperación de contraseña)
    * /auth: Autenticación y autorización
    * /similarity: Búsqueda de casos similares
    * /rag: Consultas inteligentes con RAG
    * /bitacora: Historial de actividades

Middleware:
    * CORS: Permite solicitudes desde frontend (Next.js)

Archivos estáticos:
    * /uploads: Avatares de usuario y documentos cargados

Eventos de ciclo de vida:
    * startup: Inicializa embeddings, Milvus, modelos
    * shutdown: Guarda conversaciones activas, libera recursos

Ejecución:
    Desarrollo:
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    
    Producción:
        gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker \
                 --bind 0.0.0.0:8000

Variables de entorno requeridas:
    * EMBEDDING_MODEL: Nombre del modelo de embeddings
    * DATABASE_URL: URL de conexión a SQL Server
    * MILVUS_HOST: Host de Milvus
    * MILVUS_PORT: Puerto de Milvus
    * REDIS_URL: URL de conexión a Redis
    * OLLAMA_BASE_URL: URL del servidor Ollama

Example:
    >>> # Iniciar servidor de desarrollo
    >>> uvicorn main:app --reload
    INFO:     Uvicorn running on http://0.0.0.0:8000
    INFO:     Application startup complete.

Note:
    * El modelo de embeddings (~2.5GB) se descarga automáticamente al inicio
    * Milvus debe estar corriendo antes de iniciar la API
    * Las conversaciones se guardan automáticamente al cerrar

Ver también:
    * celery_app.py: Configuración de workers Celery
    * app/routes/: Definición de endpoints
    * app/config/config.py: Configuración general

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
"""
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

# Crear instancia de FastAPI
app = FastAPI(
    title="JusticIA API",
    description="API REST para asistente legal inteligente con RAG",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """
    Inicializa todos los recursos necesarios al arranque de la aplicación.
    
    Secuencia de inicialización:
    1. Descarga y valida el modelo de embeddings desde HuggingFace (~2.5GB)
    2. Pre-carga el modelo en memoria con inferencia de prueba (warm-up)
    3. Establece conexión con Milvus y verifica colección
    
    Raises:
        RuntimeError: Si falla la descarga del modelo, carga de embeddings o
                     conexión a Milvus. La aplicación NO iniciará si hay error.
    
    Note:
        * Este evento se ejecuta UNA VEZ al iniciar la aplicación
        * El warm-up evita latencia en la primera consulta
        * Si falla, la aplicación no iniciará (fail-fast)
    """
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
    """
    Limpia y guarda recursos al apagar la aplicación.
    
    Operaciones de cierre:
    1. Guarda todas las conversaciones activas en disco
    2. Libera recursos de memoria (modelos, conexiones)
    
    Note:
        * Este evento se ejecuta al recibir SIGTERM o SIGINT
        * Las conversaciones se persisten para mantener historial
        * Los errores se loggean pero no previenen el cierre
    """
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
    """
    Endpoint raíz de healthcheck.
    
    Verifica que la API está corriendo y responde correctamente.
    
    Returns:
        dict: Mensaje de confirmación y versión de la API.
    
    Example:
        >>> response = requests.get('http://localhost:8000/')
        >>> response.json()
        {'message': 'JusticIA API está funcionando', 'version': '1.0.0'}
    """
    return {"message": "JusticIA API está funcionando", "version": "1.0.0"}
