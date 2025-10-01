from sentence_transformers import SentenceTransformer
from app.config.config import EMBEDDING_MODEL
import os
import logging

logger = logging.getLogger(__name__)

_embeddings = None

class EmbeddingsWrapper:
    """Wrapper para hacer compatible sentence-transformers con el código async"""
    
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
