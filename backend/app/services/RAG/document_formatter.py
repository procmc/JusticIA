"""
Funciones de formateo de metadata de documentos para el LLM.

Formatea metadata de documentos en Markdown legible que el LLM puede interpretar.
Añade información contextual sobre expediente, archivo, páginas, tipo y ruta.

Formato de salida:
    **Expediente:** 24-000123-0001-PE | **Archivo:** demanda.pdf | **Pág:** 1-3
    **Tipo:** Demanda
    **Ruta:** uploads/24-000123-0001-PE/demanda.pdf
    ---
    [Contenido del documento...]
    ---

Metadata extraída:
    * expediente_numero: Número de expediente
    * archivo/ruta_archivo: Nombre del documento
    * pagina_inicio/pagina_fin: Rango de páginas
    * tipo_documento: Tipo de documento judicial
    * ruta_archivo: Ruta para descarga

Funciones:
    * format_document_with_metadata: Formatea un documento individual
    * create_expediente_header: Crea header visual de expediente

Example:
    >>> from app.services.rag.document_formatter import format_document_with_metadata
    >>> from langchain_core.documents import Document
    >>> 
    >>> doc = Document(
    ...     page_content="Contenido del documento...",
    ...     metadata={
    ...         "expediente_numero": "24-000123-0001-PE",
    ...         "ruta_archivo": "uploads/24-000123-0001-PE/demanda.pdf",
    ...         "pagina_inicio": 1,
    ...         "pagina_fin": 3,
    ...         "tipo_documento": "Demanda"
    ...     }
    ... )
    >>> formatted = format_document_with_metadata(doc)
    >>> print(formatted)

Note:
    * Usa Markdown para mejor legibilidad del LLM
    * Separa header con --- para delimitar contenido
    * Extrae nombre de archivo desde ruta si disponible
    * Maneja casos donde metadata está incompleta

Ver también:
    * app.services.rag.formatted_retriever: Usa estas funciones

Authors:
    JusticIA Team

Version:
    1.0.0 - Formateo de metadata en Markdown
"""
from langchain_core.documents import Document

def format_document_with_metadata(doc: Document) -> str:
    """
    Formatea documento con metadata visible en Markdown.
    
    Args:
        doc: Documento de LangChain con metadata.
    
    Returns:
        String con metadata formateada + contenido original.
    """
    metadata = doc.metadata
    
    # Extraer información de páginas si existe
    pagina_inicio = metadata.get("pagina_inicio")
    pagina_fin = metadata.get("pagina_fin")
    
    if pagina_inicio and pagina_fin:
        if pagina_inicio == pagina_fin:
            paginas_str = f" | **Pág:** {pagina_inicio}"
        else:
            paginas_str = f" | **Págs:** {pagina_inicio}-{pagina_fin}"
    else:
        paginas_str = ""
    
    # Tipo de documento (si existe)
    tipo_doc = metadata.get("tipo_documento", "").strip()
    tipo_doc_str = f"**Tipo:** {tipo_doc}\n" if tipo_doc else ""
    
    # Ruta del archivo (si existe)
    ruta_archivo = metadata.get("ruta_archivo", "").strip()
    ruta_str = f"**Ruta:** {ruta_archivo}\n" if ruta_archivo else ""
    
    # Usar el nombre real del archivo desde la ruta si está disponible
    if ruta_archivo:
        nombre_real_archivo = ruta_archivo.split('/')[-1]
        archivo_mostrar = nombre_real_archivo
    else:
        archivo_mostrar = metadata.get('archivo', 'N/A')
    
    # Construir header con metadata
    header = (
        f"\n**Expediente:** {metadata.get('expediente_numero', 'N/A')} | "
        f"**Archivo:** {archivo_mostrar}{paginas_str}\n"
        f"{tipo_doc_str}"
        f"{ruta_str}"
        f"---\n"
    )
    
    return f"{header}{doc.page_content}\n---\n"

def create_expediente_header(expediente_numero: str, num_docs: int) -> str:
    return (
        f"\n{'='*80}\n"
        f"EXPEDIENTE: {expediente_numero} ({num_docs} documentos)\n"
        f"{'='*80}\n"
    )
