"""
Módulo para formateo de contexto y extracción de metadatos de documentos
"""
from typing import List, Dict, Any
from langchain_core.documents import Document


def format_documents_context(docs: List[Document], max_docs: int = 8, max_chars_per_doc: int = 400) -> str:
    """
    Formatea documentos para el contexto del LLM de manera optimizada
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos a incluir
        max_chars_per_doc: Caracteres máximos por documento
    
    Returns:
        Contexto formateado como string
    """
    if not docs:
        return "No hay información disponible."
    
    context_parts = []
    # Limitar documentos para modelos pequeños
    docs_to_use = docs[:min(len(docs), max_docs)]
    
    for i, doc in enumerate(docs_to_use, 1):
        expediente = doc.metadata.get("expediente_numero", "N/A")
        archivo = doc.metadata.get("archivo", "N/A")
        
        # Truncar contenido para modelos pequeños
        content = doc.page_content
        if len(content) > max_chars_per_doc:
            content = content[:max_chars_per_doc] + "..."
        
        context_parts.append(
            f"**Doc {i}** - Exp: {expediente}\n"
            f"Archivo: {archivo}\n"
            f"{content}\n"
        )
    
    return "\n---\n".join(context_parts)

def extract_document_sources(docs: List[Document]) -> List[Dict[str, Any]]:
    """
    Extrae información de fuentes de los documentos para metadatos de respuesta
    
    Args:
        docs: Lista de documentos de LangChain
    
    Returns:
        Lista de diccionarios con información de fuentes
    """
    fuentes = []
    for doc in docs:
        fuente = {
            "expediente": doc.metadata.get("expediente_numero", ""),
            "archivo": doc.metadata.get("archivo", ""),
            "relevancia": doc.metadata.get("relevance_score", 0),
            "fragmento": _truncate_text(doc.page_content, 200)
        }
        fuentes.append(fuente)
    return fuentes

def extract_unique_expedientes(docs: List[Document]) -> List[str]:
    """
    Extrae lista de expedientes únicos de los documentos
    
    Args:
        docs: Lista de documentos de LangChain
    
    Returns:
        Lista de números de expediente únicos
    """
    expedientes = set()
    for doc in docs:
        exp_num = doc.metadata.get("expediente_numero", "")
        if exp_num and exp_num.strip():
            expedientes.add(exp_num)
    
    return list(expedientes)

def _truncate_text(text: str, max_length: int) -> str:
    """Trunca texto a longitud máxima con elipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_context_compact(docs: List[Document]) -> str:
    """
    Versión compacta del formateo para modelos muy pequeños
    
    Args:
        docs: Lista de documentos de LangChain
    
    Returns:
        Contexto ultra-compacto
    """
    if not docs:
        return "Sin información."
    
    context_parts = []
    # Solo 5 documentos para modelos muy pequeños
    for i, doc in enumerate(docs[:5], 1):
        exp = doc.metadata.get("expediente_numero", "N/A")
        # Solo 200 caracteres por documento
        content = _truncate_text(doc.page_content, 200)
        context_parts.append(f"**{i}.** Exp:{exp} - {content}")
    
    return "\n\n".join(context_parts)