"""
Módulo de embeddings para JusticIA.

Proporciona generación de vectores usando BGE-M3 (sentence-transformers)
con adaptador para LangChain.

Módulos:
    * embeddings.py: Servicio principal con lazy loading
    * langchain_adapter.py: Adaptador para interfaz LangChain

Modelo:
    * Nombre: Dariolopez/bge-m3-es-legal-tmp-6
    * Base: BAAI/bge-m3 (BGE-M3)
    * Dimensiones: 1024
    * Idioma: Español optimizado para legal
    * Tamaño: ~2.3 GB
    * Similitud: Coseno (normalizado)

Características:
    * Lazy loading: Carga bajo demanda
    * Cache local: Pre-descarga en Docker
    * Async compatible: Wrapper para sentence-transformers
    * LangChain compatible: Adaptador incluido
    * GPU acelerado: CUDA si disponible

Uso:
    >>> from app.embeddings.embeddings import get_embeddings, get_embedding
    >>> from app.embeddings.langchain_adapter import LangChainEmbeddingsAdapter
    >>> 
    >>> # Servicio directo
    >>> embeddings = await get_embeddings()
    >>> vector = await embeddings.aembed_query("consulta")
    >>> 
    >>> # Función de conveniencia
    >>> vector = await get_embedding("texto")
    >>> 
    >>> # Adaptador LangChain
    >>> lc_embeddings = LangChainEmbeddingsAdapter()
    >>> docs_vectors = lc_embeddings.embed_documents(["doc1", "doc2"])

Note:
    * Primera carga tarda ~5-10s
    * Modelo persiste en memoria del proceso
    * GPU acelera 5-10x si disponible
    * Cache local evita download en producción

Ver también:
    * app.vectorstore.milvus_storage: Usa embeddings
    * app.services.rag.retriever: Usa para búsqueda
    * app.config.config: EMBEDDING_MODEL configurado
    * utils/hf_model.py: Pre-descarga del modelo

Authors:
    JusticIA Team

Version:
    1.0.0 - BGE-M3 con LangChain adapter
"""
