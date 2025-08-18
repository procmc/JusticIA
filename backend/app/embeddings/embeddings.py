from langchain_huggingface import HuggingFaceEmbeddings
from app.config.config import EMBEDDING_MODEL

_embeddings = None

async def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings
