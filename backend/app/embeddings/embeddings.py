"""
Generación de embeddings con sentence-transformers.

Proporciona servicio de embeddings usando BGE-M3 (o modelo configurado)
con lazy loading y compatibilidad async.

Características:
    * Modelo: BGE-M3 (Dariolopez/bge-m3-es-legal-tmp-6)
    * Dimensiones: 1024
    * Idioma: Español optimizado para legal
    * Lazy loading: Carga bajo demanda
    * Cache local: Pre-descarga en Docker
    * Async compatible: Wrapper para sentence-transformers

Modelo BGE-M3:
    * BAAI General Embedding v3 (Multi-lingual)
    * Fine-tuned para documentos legales en español
    * Dense retrieval (vectores densos)
    * Normalizado: Similitud coseno directa
    * Tamaño: ~2.3 GB

Cache local:
    * Ruta: /app/models/{EMBEDDING_MODEL}
    * Pre-descarga: utils/hf_model.py
    * Evita download en runtime (producción)
    * Fallback: HuggingFace si no existe local

Lazy loading:
    * Variable global _embeddings
    * Se carga en primera llamada
    * Persiste en memoria del proceso
    * Compartido entre requests

Example:
    >>> from app.embeddings.embeddings import get_embeddings, get_embedding
    >>> 
    >>> # Obtener servicio
    >>> embeddings = await get_embeddings()
    >>> 
    >>> # Embedding de consulta
    >>> vector = await embeddings.aembed_query("¿Qué dice la sentencia?")
    >>> print(len(vector))  # 1024
    >>> 
    >>> # Embeddings de documentos
    >>> vectors = await embeddings.aembed_documents([
    ...     "Documento 1...",
    ...     "Documento 2..."
    ... ])
    >>> 
    >>> # Función de conveniencia
    >>> vector = await get_embedding("Texto a vectorizar")

Note:
    * Primera carga tarda ~5-10s (cargar modelo 2.3GB)
    * Encode batch más eficiente que individual
    * GPU acelera 5-10x (CUDA compatible)
    * Vectors son listas Python (JSON serializable)
    * Normalización automática por sentence-transformers

Ver también:
    * app.embeddings.langchain_adapter: Adaptador para LangChain
    * app.vectorstore.milvus_storage: Usa embeddings
    * app.config.config: EMBEDDING_MODEL configurado
    * utils/hf_model.py: Pre-descarga del modelo

Authors:
    JusticIA Team

Version:
    1.0.0 - BGE-M3 con lazy loading
"""
from sentence_transformers import SentenceTransformer
from app.config.config import EMBEDDING_MODEL
import os
import logging

logger = logging.getLogger(__name__)

_embeddings = None

class EmbeddingsWrapper:
    """
    Wrapper async para sentence-transformers.
    
    Hace compatible sentence-transformers (síncrono) con
    código async de FastAPI.
    
    Attributes:
        model (SentenceTransformer): Modelo sentence-transformers cargado.
    """
    
    def __init__(self, model):
        self.model = model
    
    async def aembed_query(self, text: str):
        """Genera embedding para una consulta de texto"""
        return self.model.encode(text).tolist()
    
    async def aembed_documents(self, texts: list):
        """Genera embeddings para múltiples documentos"""
        return self.model.encode(texts).tolist()

async def get_embeddings():
    global _embeddings
    if _embeddings is None:
        logger.info(f"Cargando modelo de embeddings: {EMBEDDING_MODEL}")
        
        # Ruta local donde se pre-descarga el modelo (ver utils/hf_model.py)
        local_model_path = f"/app/models/{EMBEDDING_MODEL.replace('/', '__')}"
        
        # Intentar cargar desde ruta local primero (más rápido)
        if os.path.exists(local_model_path):
            logger.info(f"Cargando modelo desde cache local: {local_model_path}")
            model = SentenceTransformer(local_model_path)
        else:
            # Si no existe localmente, SentenceTransformer lo descarga automáticamente
            # (esto puede tomar varios minutos la primera vez)
            logger.warning(f"Modelo no encontrado localmente, descargando desde HuggingFace...")
            logger.warning(f"Esto puede tomar varios minutos. Considera pre-descargar el modelo.")
            model = SentenceTransformer(EMBEDDING_MODEL)
        
        logger.info("Modelo de embeddings cargado exitosamente")
        _embeddings = EmbeddingsWrapper(model)
    return _embeddings

async def get_embedding(text: str) -> list:
    """
    Función de conveniencia para generar embedding de un texto.
    Compatible con el servicio de consulta general.
    """
    embeddings = await get_embeddings()
    return await embeddings.aembed_query(text)
