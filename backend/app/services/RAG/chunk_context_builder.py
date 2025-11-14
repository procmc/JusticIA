"""
Constructor de contexto estructurado agrupando chunks por documento.

Formatea documentos recuperados agrupando chunks del mismo archivo fuente
para presentación legible al LLM con metadata completa.

Características:
    * Agrupa chunks por documento de origen (id_documento + nombre_archivo)
    * Ordena chunks por indice_chunk dentro de cada documento
    * Truncamiento inteligente de chunks largos
    * Detección de audio transcrito
    * Limpieza de timestamps y marcas de audio

Estructura de salida:
    **CONTEXTO ESTRUCTURADO**
    Documentos: 3 | Chunks totales: 8
    
    ====================================================================================================
    **DOCUMENTO 1**
    Archivo: demanda.pdf
    Expediente: 24-000123-0001-PE
    Mostrando chunks: 1-3 de 5 totales
    ====================================================================================================
    **[CHUNK 1]** (Pags. 1-2, 1,234 chars)
    [Contenido...]
    
    **[CHUNK 2]** (Pags. 3-4, 987 chars)
    [Contenido...]

Limpieza de audio transcrito:
    * Elimina timestamps: [00:12:34]
    * Normaliza marcas: [ruido] → [sonido ambiente]
    * Normaliza inaudibles: [inaudible]

Truncamiento inteligente:
    * Busca fin de oración cercano al límite
    * Fallback a espacio más cercano
    * Añade "..." si se trunca

Example:
    >>> from app.services.rag.chunk_context_builder import format_documents_by_chunks
    >>> from langchain_core.documents import Document
    >>> 
    >>> docs = [
    ...     Document(
    ...         page_content="Contenido chunk 1...",
    ...         metadata={
    ...             "id_documento": 123,
    ...             "nombre_archivo": "demanda.pdf",
    ...             "indice_chunk": 0,
    ...             "pagina_inicio": 1,
    ...             "pagina_fin": 2
    ...         }
    ...     ),
    ...     # ...
    ... ]
    >>> contexto = format_documents_by_chunks(docs, max_docs=20)
    >>> print(contexto)

Note:
    * Usado por versiones antiguas de RAG (pre-FormattedRetriever)
    * FormattedRetriever es el approach actual
    * Se mantiene para compatibilidad con código legacy
    * max_chars_per_chunk: 800 por defecto

Ver también:
    * app.services.rag.formatted_retriever: Approach moderno
    * app.services.rag.document_formatter: Formateo actual

Authors:
    JusticIA Team

Version:
    1.0.0 - Constructor de contexto estructurado (legacy)
"""
from typing import List
from langchain_core.documents import Document
from collections import defaultdict
import re


def format_documents_by_chunks(
    """
    Formatea documentos agrupando chunks por archivo.
    
    Args:
        docs: Lista de documentos recuperados.
        max_docs: Máximo de documentos a incluir.
        max_chars_per_chunk: Máximo de caracteres por chunk.
    
    Returns:
        String con contexto estructurado formateado.
    """
    docs: List[Document], 
    max_docs: int = 20, 
    max_chars_per_chunk: int = 800
) -> str:
    if not docs:
        return "No hay información disponible."
    
    # Paso 1: Agrupar chunks por documento
    docs_by_file = _group_chunks_by_document(docs[:max_docs])
    
    # Paso 2: Ordenar chunks dentro de cada documento
    _sort_chunks_within_documents(docs_by_file)
    
    # Paso 3: Formatear contexto estructurado
    return _format_grouped_documents(docs_by_file, max_chars_per_chunk)


def _group_chunks_by_document(docs: List[Document]) -> dict:
    docs_by_file = defaultdict(list)
    
    for doc in docs:
        # Extraer identificadores del documento
        id_doc = doc.metadata.get("id_documento", "unknown")
        nombre_archivo = doc.metadata.get("nombre_archivo", doc.metadata.get("archivo", "Sin nombre"))
        
        # Crear clave única por documento
        doc_key = f"{id_doc}_{nombre_archivo}"
        docs_by_file[doc_key].append(doc)
    
    return docs_by_file


def _sort_chunks_within_documents(docs_by_file: dict) -> None:
    for doc_key in docs_by_file:
        docs_by_file[doc_key].sort(
            key=lambda d: d.metadata.get("indice_chunk", 0)
        )


def _format_grouped_documents(docs_by_file: dict, max_chars_per_chunk: int) -> str:
    context_parts = []
    doc_counter = 0
    total_chunks_shown = 0
    
    for doc_key, chunks in docs_by_file.items():
        doc_counter += 1
        
        # Extraer metadata del documento (del primer chunk)
        doc_metadata = _extract_document_metadata(chunks[0])
        
        # Determinar rango de chunks mostrados
        chunk_range = _calculate_chunk_range(chunks)
        
        # Header del documento
        context_parts.append(_format_document_header(
            doc_counter=doc_counter,
            metadata=doc_metadata,
            chunk_range=chunk_range
        ))
        
        # Formatear cada chunk del documento
        for chunk in chunks:
            context_parts.append(_format_single_chunk(
                chunk=chunk,
                es_audio=doc_metadata['es_audio'],
                max_chars=max_chars_per_chunk
            ))
            total_chunks_shown += 1
    
    # Header global
    header = _format_global_header(doc_counter, total_chunks_shown)
    
    return header + "".join(context_parts)


def _extract_document_metadata(first_chunk: Document) -> dict:
    """
    Extrae metadata relevante del documento desde el primer chunk.
    """
    nombre_archivo = first_chunk.metadata.get("nombre_archivo", first_chunk.metadata.get("archivo", "Sin nombre"))
    tipo_archivo = first_chunk.metadata.get("tipo_archivo", "")
    expediente = first_chunk.metadata.get("numero_expediente", first_chunk.metadata.get("expediente_numero", "Sin expediente"))
    total_chunks = first_chunk.metadata.get("meta", {}).get("total_chunks", 1)
    
    es_audio = _is_audio_file(tipo_archivo, nombre_archivo)
    tipo_doc_label = "AUDIO TRANSCRITO" if es_audio else "DOCUMENTO"
    
    return {
        'nombre_archivo': nombre_archivo,
        'tipo_doc_label': tipo_doc_label,
        'expediente': expediente,
        'total_chunks': total_chunks,
        'es_audio': es_audio
    }


def _is_audio_file(tipo_archivo, nombre_archivo: str) -> bool:
    """Detecta si el archivo es audio transcrito."""
    if tipo_archivo in [3, 4, 5, 6]:
        return True
    
    audio_extensions = ['.mp3', '.wav', '.ogg', '.m4a']
    return any(ext in nombre_archivo.lower() for ext in audio_extensions)


def _calculate_chunk_range(chunks: List[Document]) -> str:
    """Calcula el rango de chunks mostrados."""
    indices_chunks = [c.metadata.get("indice_chunk", i) for i, c in enumerate(chunks)]
    
    if len(indices_chunks) > 1:
        return f"{min(indices_chunks)+1}-{max(indices_chunks)+1}"
    else:
        return f"{indices_chunks[0]+1}"


def _format_global_header(doc_count: int, chunk_count: int) -> str:
    """Formatea el header global del contexto."""
    return (
        f"**CONTEXTO ESTRUCTURADO**\n"
        f"Documentos: {doc_count} | Chunks totales: {chunk_count}\n"
    )


def _format_document_header(doc_counter: int, metadata: dict, chunk_range: str) -> str:
    """Formatea el header de un documento específico."""
    return (
        f"\n{'='*100}\n"
        f"**{metadata['tipo_doc_label']} {doc_counter}**\n"
        f"Archivo: {metadata['nombre_archivo']}\n"
        f"Expediente: {metadata['expediente']}\n"
        f"Mostrando chunks: {chunk_range} de {metadata['total_chunks']} totales\n"
        f"{'='*100}\n"
    )


def _format_single_chunk(chunk: Document, es_audio: bool, max_chars: int) -> str:
    """Formatea un chunk individual con su metadata."""
    indice_chunk = chunk.metadata.get("indice_chunk", 0)
    pagina_inicio = chunk.metadata.get("pagina_inicio", "N/A")
    pagina_fin = chunk.metadata.get("pagina_fin", "N/A")
    chunk_length = len(chunk.page_content)
    
    content = _clean_chunk_content(chunk.page_content, es_audio, max_chars)
    
    return (
        f"**[CHUNK {indice_chunk+1}]** (Pags. {pagina_inicio}-{pagina_fin}, {chunk_length:,} chars)\n"
        f"{content}\n\n"
    )


def _clean_chunk_content(content: str, es_audio: bool, max_length: int) -> str:
    """Limpia contenido de chunk, manejando casos especiales."""
    cleaned = re.sub(r'\s+', ' ', content)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
    
    if es_audio:
        cleaned = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', cleaned)
        cleaned = re.sub(r'\[.*?ruido.*?\]', '[sonido ambiente]', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[.*?inaudible.*?\]', '[inaudible]', cleaned, flags=re.IGNORECASE)
    
    if len(cleaned) > max_length:
        cleaned = _truncate_smart(cleaned, max_length)
    
    return cleaned.strip()


def _truncate_smart(text: str, max_length: int) -> str:
    """Trunca texto buscando fin de oración cercano al límite."""
    truncated = text[:max_length]
    
    last_period = truncated.rfind('.')
    if last_period > max_length - 100:
        return truncated[:last_period + 1]
    
    last_space = truncated.rfind(' ')
    if last_space > max_length - 50:
        return truncated[:last_space] + "..."
    
    return truncated + "..."
