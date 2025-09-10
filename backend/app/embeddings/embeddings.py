from sentence_transformers import SentenceTransformer
from app.config.config import EMBEDDING_MODEL

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
        model = SentenceTransformer(EMBEDDING_MODEL)
        _embeddings = EmbeddingsWrapper(model)
    return _embeddings

async def get_embedding(text: str) -> list:
    """
    Función de conveniencia para generar embedding de un texto.
    Compatible con el servicio de consulta general.
    """
    embeddings = await get_embeddings()
    return await embeddings.aembed_query(text)
