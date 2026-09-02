"""
Módulo de vectorstore con (Milvus / Qdrant) y LangChain.

Proporciona acceso a la base de datos vectorial activa (Milvus o Qdrant, según
VECTORSTORE_BACKEND) para almacenamiento y recuperación de embeddings de 
documentos judiciales, a través de una interfaz común.

Componentes:
    * base.py: Interfaz abstracta VectorStoreBackend (contrato común)
    * milvus_backend.py: Implementación sobre Milvus (motor original)
    * qdrant_backend.py: Implementación sobre Qdrant (motor nuevo, Fase 2)
    * vectorstore.py: Cliente Milvus con búsquedas y gestión (usado por milvus_backend)
    * milvus_storage.py: Almacenamiento con chunking automático
    * schema.py: Definición del schema de colección (Milvus)

Tecnologías:
    * Milvus / Qdrant: Bases de datos vectoriales (intercambiables)
    * LangChain: Orquestación y embeddings automáticos
    * multilingual-e5-large: Modelo de embeddings multilingüe (no chino)

Funcionalidades principales:
    * Selección del backend activo por variable de entorno (VECTORSTORE_BACKEND)
    * Búsqueda semántica por similitud coseno
    * Búsqueda por expediente específico
    * Búsqueda de expedientes similares
    * Almacenamiento con chunking inteligente
    * Filtrado automático por estado procesado

Example:
    >>> from app.vectorstore import get_vectorstore_backend
    >>>
    >>> # Obtener el backend activo (Milvus o Qdrant según configuración)
    >>> backend = get_vectorstore_backend()
    >>>
    >>> # Búsqueda
    >>> results = await backend.search_by_text("¿Qué es la prescripción?")
    >>>
    >>> # Almacenamiento
    >>> ids = await backend.add_documents(documentos)

Ver también:
    * app.vectorstore.base: Contrato VectorStoreBackend
    * app.services.rag: Usa vectorstore para RAG
    * app.services.ingesta: Almacena documentos procesados
    * app.embeddings: Genera embeddings

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz
    Andrés Araya Agüero
Version:
    3.0.0 - Backend conmutable Milvus/Qdrant
"""

from app.config.config import VECTORSTORE_BACKEND


def get_vectorstore_backend():
    """Devuelve la instancia del backend vectorial activo según VECTORSTORE_BACKEND."""
    if VECTORSTORE_BACKEND == "qdrant":
        from app.vectorstore.qdrant_backend import QdrantBackend
        return QdrantBackend()

    from app.vectorstore.milvus_backend import MilvusBackend
    return MilvusBackend()