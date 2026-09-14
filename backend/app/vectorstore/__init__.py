"""
Módulo de vectorstore (Qdrant) con LangChain.

Proporciona acceso a la base de datos vectorial (Qdrant) para almacenamiento
y recuperación de embeddings de documentos, a través de una interfaz común.

Componentes:
    * base.py: Interfaz abstracta VectorStoreBackend (contrato común)
    * qdrant_backend.py: Implementación sobre Qdrant (único motor vectorial)
    * storage.py: Chunking y preparación de metadata para almacenamiento

Tecnologías:
    * Qdrant: Base de datos vectorial
    * LangChain: Orquestación y embeddings automáticos
    * multilingual-e5-large: Modelo de embeddings multilingüe (no chino)

Funcionalidades principales:
    * Búsqueda semántica por similitud coseno
    * Búsqueda por expediente específico
    * Búsqueda de expedientes similares
    * Almacenamiento con chunking inteligente
    * Filtrado automático por estado procesado

Example:
    >>> from app.vectorstore import get_vectorstore_backend
    >>>
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
    4.0.0 - Milvus retirado; Qdrant como único backend vectorial
"""


def get_vectorstore_backend():
    """Devuelve la instancia del backend vectorial activo (Qdrant)."""
    from app.vectorstore.qdrant_backend import QdrantBackend
    return QdrantBackend()
