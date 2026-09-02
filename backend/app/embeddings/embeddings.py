"""
Generación de embeddings con sentence-transformers (modelo configurable).

Proporciona servicio de embeddings usando el modelo definido en EMBEDDING_MODEL,
con lazy loading, compatibilidad async, y soporte para los prefijos "query:"/
"passage:" que exige la familia de modelos E5.

Características:
    * Modelo actual: multilingual-e5-large (Microsoft/intfloat)
    * Dimensiones: 1024
    * Prefijos E5: agregados automáticamente si el modelo pertenece a la familia E5
    * Lazy loading: Carga bajo demanda
    * Cache local: Pre-descarga en Docker
    * Async compatible: Wrapper para sentence-transformers

Cambio de modelo (Fase 2):
    * Modelo anterior: BGE-M3 (Dariolopez/bge-m3-es-legal-tmp-6) — origen chino (BAAI)
    * Modelo actual: multilingual-e5-large — origen no chino, misma dimensión (1024)
    * Justificación técnica completa: ver Registro_Indicaciones/16_Investigacion_Modelo_Embeddings.md
    * Detalle importante: los modelos E5 requieren prefijar el texto con "query: "
      (consultas) o "passage: " (documentos) para un desempeño óptimo — manejado
      automáticamente por EmbeddingsWrapper según el nombre del modelo configurado.

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
    >>> # Embedding de consulta (se le agrega "query: " automáticamente si aplica)
    >>> vector = await embeddings.aembed_query("¿Qué dice la sentencia?")
    >>> print(len(vector))  # 1024
    >>> 
    >>> # Embeddings de documentos (se les agrega "passage: " automáticamente si aplica)
    >>> vectors = await embeddings.aembed_documents([
    ...     "Documento 1...",
    ...     "Documento 2..."
    ... ])
    >>> 
    >>> # Función de conveniencia
    >>> vector = await get_embedding("Texto a vectorizar")

Note: 
    * Primera carga tarda ~5-10s (cargar modelo 2GB)
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
    Andrés Araya Agüero
Version:
    2.0.0 - Modelo configurable + soporte de prefijos E5
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

    def __init__(self, model, model_name: str = ""):
        self.model = model
        # multilingual-e5-large (y la familia E5) requiere prefijos "query:"/"passage:"
        self._use_e5_prefix = "e5" in model_name.lower()

    async def aembed_query(self, text: str):
        """Genera embedding para una consulta de texto"""
        if self._use_e5_prefix:
            text = f"query: {text}"
        return self.model.encode(text).tolist()

    async def aembed_documents(self, texts: list):
        """Genera embeddings para múltiples documentos"""
        if self._use_e5_prefix:
            texts = [f"passage: {t}" for t in texts]
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
        _embeddings = EmbeddingsWrapper(model, EMBEDDING_MODEL)
    return _embeddings

async def get_embedding(text: str) -> list:
    """
    Función de conveniencia para generar embedding de un texto.
    Compatible con el servicio de consulta general.
    """
    embeddings = await get_embeddings()
    return await embeddings.aembed_query(text)
