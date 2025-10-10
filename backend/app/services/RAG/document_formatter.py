"""
Utilidades para formatear documentos con metadata para el LLM.

Este módulo proporciona funciones para agregar metadata visible
(expediente, archivo, chunk, páginas) al contenido de los documentos
antes de enviarlos al LLM.
"""
from langchain_core.documents import Document


def format_document_with_metadata(doc: Document) -> str:
    """
    Formatea un documento con su metadata visible para el LLM.
    
    Args:
        doc: Documento de LangChain con metadata
        
    Returns:
        str: Contenido formateado con header de metadata
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
    
    # Construir header con metadata
    header = (
        f"\n**Expediente:** {metadata.get('expediente_numero', 'N/A')} | "
        f"**Archivo:** {metadata.get('archivo', 'N/A')} | "
        f"**Chunk:** {metadata.get('indice_chunk', 0)}{paginas_str}\n"
        f"{tipo_doc_str}"
        f"---\n"
    )
    
    return f"{header}{doc.page_content}\n---\n"


def create_expediente_header(expediente_numero: str, num_docs: int) -> str:
    """
    Crea un header visual para agrupar documentos de un expediente.
    
    Args:
        expediente_numero: Número del expediente
        num_docs: Cantidad de documentos del expediente
        
    Returns:
        str: Header formateado
    """
    return (
        f"\n{'='*80}\n"
        f"EXPEDIENTE: {expediente_numero} ({num_docs} documentos)\n"
        f"{'='*80}\n"
    )
