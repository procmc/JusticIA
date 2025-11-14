"""
Módulo de vectorstore con Milvus y LangChain.

Proporciona acceso a la base de datos vectorial Milvus para almacenamiento
y recuperación de embeddings de documentos judiciales.

Componentes:
    * vectorstore.py: Cliente principal con búsquedas y gestión
    * milvus_storage.py: Almacenamiento con chunking automático
    * schema.py: Definición del schema de colección

Tecnologías:
    * Milvus: Base de datos vectorial de alto rendimiento
    * LangChain: Orquestación y embeddings automáticos
    * BGE-M3: Modelo de embeddings multilingüe

Funcionalidades principales:
    * Búsqueda semántica por similitud coseno
    * Búsqueda por expediente específico
    * Búsqueda de expedientes similares
    * Almacenamiento con chunking inteligente
    * Filtrado automático por estado procesado

Example:
    >>> from app.vectorstore import search_by_text, store_in_vectorstore
    >>> 
    >>> # Búsqueda
    >>> results = await search_by_text("¿Qué es la prescripción?")
    >>> 
    >>> # Almacenamiento
    >>> ids, chunks = await store_in_vectorstore(
    ...     texto="contenido",
    ...     metadatos={...},
    ...     CT_Num_expediente="24-000123-0001-PE",
    ...     id_expediente=123,
    ...     id_documento=456
    ... )

Ver también:
    * app.services.rag: Usa vectorstore para RAG
    * app.services.ingesta: Almacena documentos procesados
    * app.embeddings: Genera embeddings

Authors:
    JusticIA Team

Version:
    2.0.0 - Integración LangChain
"""
