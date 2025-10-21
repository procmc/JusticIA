from langchain_core.documents import Document

def format_document_with_metadata(doc: Document) -> str:
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
        f"**Archivo:** {archivo_mostrar} | "
        f"**Chunk:** {metadata.get('indice_chunk', 0)}{paginas_str}\n"
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
