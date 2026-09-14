"""
Almacenamiento vectorial con chunking y metadata enriquecida.

Usa LangChain para automatizar embeddings e inserción. Maneja chunking
inteligente, estimación de páginas y preparación de metadata, delegando el
almacenamiento real al backend vectorial activo (Qdrant, vía
get_vectorstore_backend()).

Características:
    * Chunking con RecursiveCharacterTextSplitter
    * Chunks de 7000 chars, overlap de 500 chars para continuidad contextual
    * Estimación de páginas por chunk
    * Metadata completa (expediente, documento, chunk, páginas)
    * Embeddings automáticos via LangChain

Flujo de almacenamiento:
    1. Recibir texto completo del documento
    2. Dividir en chunks con text_splitter
    3. Calcular páginas estimadas por chunk
    4. Preparar metadata enriquecida
    5. Crear Documents de LangChain
    6. Llamar add_documents del backend activo (embeddings automáticos)

Metadata por chunk:
    * id_chunk: UUID único
    * id_expediente/numero_expediente: Referencias a BD
    * id_documento/nombre_archivo: Identificación del documento
    * indice_chunk: Posición secuencial
    * pagina_inicio/pagina_fin: Rango estimado de páginas
    * tipo_archivo: Código de tipo (FILE_TYPE_CODES)
    * fecha_carga/fecha_vectorizacion: Timestamps
    * meta: JSON con info adicional (total_chunks, length, etc.)

Chunking:
    * Separadores: \n\n, \n, ".", " " (en orden de preferencia)
    * Respeta límites de oración cuando es posible
    * Overlap mantiene continuidad entre chunks
    * Longitud función: len (caracteres)

Estimación de páginas:
    * 2500 caracteres por página (aprox 500 palabras)
    * Cálculo basado en posición de caracteres
    * Mantiene secuencia correcta entre chunks

Example:
    >>> from app.vectorstore.storage import store_in_vectorstore
    >>>
    >>> texto = "Contenido del documento..." * 1000
    >>> metadatos = {
    ...     "nombre_archivo": "demanda.pdf",
    ...     "ruta_archivo": "uploads/24-000123-0001-PE/demanda.pdf",
    ...     "tipo": "PDF"
    ... }
    >>> ids, num_chunks = await store_in_vectorstore(
    ...     texto=texto,
    ...     metadatos=metadatos,
    ...     CT_Num_expediente="24-000123-0001-PE",
    ...     id_expediente=123,
    ...     id_documento=456
    ... )
    >>> print(f"Almacenados {num_chunks} chunks con IDs {len(ids)}")

Note:
    * LangChain genera embeddings automáticamente (multilingual-e5-large)
    * IDs retornados son asignados por el backend vectorial activo
    * Metadata "meta" es JSON flexible para extensibilidad

Ver también:
    * app.vectorstore: get_vectorstore_backend() para inserción
    * app.config.file_config: FILE_TYPE_CODES
    * app.services.ingesta: Usa store_in_vectorstore

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz
    Andrés Araya Agüero

Version:
    3.0.0 - Desacoplado de Milvus; usa get_vectorstore_backend()
"""

import uuid
import time
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config.file_config import FILE_TYPE_CODES
from app.vectorstore import get_vectorstore_backend
from pathlib import Path

async def store_in_vectorstore(
    texto: str,
    metadatos: dict,
    CT_Num_expediente: str,
    id_expediente: int,  # ID real de la BD
    id_documento: int    # ID real de la BD
) -> tuple[list, int]:
    """
    Almacena documento en el backend vectorial activo con chunking y embeddings automáticos.

    Procesa texto completo dividiéndolo en chunks, preparando metadata
    enriquecida y almacenando con embeddings generados automáticamente
    por LangChain.

    Beneficios LangChain:
        * Embeddings automáticos (sin código manual del modelo)
        * Inserción optimizada en batch
        * Gestión de errores integrada
        * Retry automático en fallos

    Args:
        texto: Texto completo del documento extraído (PDF/audio transcrito).
        metadatos: Dict con nombre_archivo, ruta_archivo, tipo, etc.
        CT_Num_expediente: Número de expediente formato YY-NNNNNN-NNNN-XX.
        id_expediente: ID del expediente en T_Expediente (FK).
        id_documento: ID del documento en T_Documento (FK).

    Returns:
        tuple[list, int]: (Lista de IDs asignados, Número de chunks creados)

    Raises:
        Exception: Error en chunking o almacenamiento en el vectorstore.

    Example:
        >>> metadatos = {
        ...     "nombre_archivo": "demanda.pdf",
        ...     "ruta_archivo": "uploads/24-000123-0001-PE/demanda.pdf"
        ... }
        >>> ids, num_chunks = await store_in_vectorstore(
        ...     texto=texto_extraido,
        ...     metadatos=metadatos,
        ...     CT_Num_expediente="24-000123-0001-PE",
        ...     id_expediente=123,
        ...     id_documento=456
        ... )
        >>> print(f"{num_chunks} chunks almacenados")

    Note:
        * Chunks de 7000 chars con overlap de 500
        * Estimación de páginas: 2500 caracteres por página
        * Metadata "meta" es JSON flexible para extensibilidad
        * Timestamps en epoch milliseconds
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=7000,
        chunk_overlap=500,    # Mayor overlap para mantener continuidad
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]  # Separadores en orden de preferencia
    )

    # Dividir el texto en chunks
    chunks = text_splitter.split_text(texto)
    print(f"Documento dividido en {len(chunks)} chunks para LangChain")

    # Preparar metadatos comunes
    timestamp_ms = int(time.time() * 1000)
    extension = Path(metadatos["nombre_archivo"]).suffix.lower()
    tipo_archivo_codigo = FILE_TYPE_CODES.get(extension, 1)

    # Estimar páginas aproximadas
    caracteres_por_pagina = 2500  # Aproximadamente 500 palabras x 5 chars/palabra

    # Crear documentos LangChain para cada chunk
    langchain_documents = []

    for i, chunk_text in enumerate(chunks):
        # Calcular páginas aproximadas para este chunk
        inicio_char = i * (7000 - 500)  # chunk_size menos overlap
        fin_char = inicio_char + len(chunk_text)

        pagina_inicio = max(1, (inicio_char // caracteres_por_pagina) + 1)
        pagina_fin = max(pagina_inicio, (fin_char // caracteres_por_pagina) + 1)

        # Metadatos específicos del chunk para LangChain
        chunk_metadata = {
            # IDs únicos
            "id_chunk": str(uuid.uuid4()),

            # Referencias a BD transaccional
            "id_expediente": id_expediente,
            "numero_expediente": CT_Num_expediente,
            "fecha_expediente_creacion": timestamp_ms,
            "id_documento": id_documento,
            "nombre_archivo": metadatos["nombre_archivo"],
            "tipo_archivo": tipo_archivo_codigo,
            "fecha_carga": timestamp_ms,

            # Info del chunk
            "indice_chunk": i,
            "pagina_inicio": pagina_inicio,
            "pagina_fin": pagina_fin,
            "tipo_documento": "documento",
            "fecha_vectorizacion": timestamp_ms,

            # Metadatos flexibles
            "meta": {
                **metadatos,
                "total_chunks": len(chunks),
                "chunk_index": i,
                "chunk_length": len(chunk_text),
                "estimated_pages": f"{pagina_inicio}-{pagina_fin}"
            }
        }

        # Crear documento LangChain
        document = Document(
            page_content=chunk_text,
            metadata=chunk_metadata
        )
        langchain_documents.append(document)

    # El backend activo (Qdrant) maneja embeddings automáticamente
    if langchain_documents:
        doc_ids = await get_vectorstore_backend().add_documents(langchain_documents)
        print(f"{len(doc_ids)} chunks almacenados para {metadatos['nombre_archivo']}")
        return doc_ids, len(chunks)  # Retornar IDs y número de chunks

    return [], 0  # Sin documentos procesados
