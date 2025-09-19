"""
Módulo para formateo de contexto y extracción de metadatos de documentos
"""
from typing import List, Dict, Any
from langchain_core.documents import Document


def format_documents_context(docs: List[Document], max_docs: int = 12, max_chars_per_doc: int = 600) -> str:
    """
    Formatea documentos para el contexto del LLM - Optimizado para Poder Judicial CR
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos a incluir (12 para casos judiciales)
        max_chars_per_doc: Caracteres máximos por documento (600 para más información legal)
    
    Returns:
        Contexto formateado como string
    """
    if not docs:
        return "No hay información disponible."
    
    context_parts = []
    # Limitar documentos para modelos pequeños
    docs_to_use = docs[:min(len(docs), max_docs)]
    
    for i, doc in enumerate(docs_to_use, 1):
        expediente = doc.metadata.get("expediente_numero", "Sin expediente")
        archivo = doc.metadata.get("archivo", "Sin archivo")
        materia = doc.metadata.get("materia", "Sin especificar")
        sede_judicial = doc.metadata.get("sede_judicial", "Sin sede")
        fecha = doc.metadata.get("fecha", "Sin fecha")
        tipo_documento = doc.metadata.get("tipo_documento", "Sin tipo")
        
        # Truncar contenido para modelos pequeños
        content = doc.page_content
        if len(content) > max_chars_per_doc:
            content = content[:max_chars_per_doc] + "..."
        
        context_parts.append(
            f"**Documento {i}**\n"
            f"• Expediente: {expediente}\n"
            f"• Materia: {materia}\n"
            f"• Sede Judicial: {sede_judicial}\n"
            f"• Tipo de Documento: {tipo_documento}\n"
            f"• Fecha: {fecha}\n"
            f"• Archivo: {archivo}\n"
            f"• Contenido: {content}\n"
        )
    
    return "\n" + "="*60 + "\n".join(context_parts)

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
            "materia": doc.metadata.get("materia", ""),
            "sede_judicial": doc.metadata.get("sede_judicial", ""),
            "fecha": doc.metadata.get("fecha", ""),
            "tipo_documento": doc.metadata.get("tipo_documento", ""),
            "relevancia": doc.metadata.get("relevance_score", 0),
            "fragmento": _truncate_text(doc.page_content, 300)  # Aumentado para más contexto
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

def extract_materias_judiciales(docs: List[Document]) -> List[str]:
    """
    Extrae las materias judiciales únicas de los documentos
    
    Args:
        docs: Lista de documentos de LangChain
    
    Returns:
        Lista de materias judiciales únicas ordenadas
    """
    materias = set()
    for doc in docs:
        materia = doc.metadata.get("materia", "")
        if materia and materia.strip():
            materias.add(materia.strip())
    
    return sorted(list(materias))

def _truncate_text(text: str, max_length: int) -> str:
    """Trunca texto a longitud máxima con elipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def format_context_compact(docs: List[Document], max_docs: int = 8) -> str:
    """
    Versión compacta del formateo para modelos muy pequeños - Optimizada para Poder Judicial CR
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos a incluir (8 para casos judiciales)
    
    Returns:
        Contexto ultra-compacto con información detallada del expediente
    """
    if not docs:
        return "Sin información de expedientes disponible."
    
    context_parts = []
    # Usar parámetro configurable en lugar de hardcoded 5
    for i, doc in enumerate(docs[:max_docs], 1):
        exp = doc.metadata.get("expediente_numero", "N/A")
        materia = doc.metadata.get("materia", "Sin especificar")
        sede = doc.metadata.get("sede_judicial", "Sin sede")
        fecha = doc.metadata.get("fecha", "Sin fecha")
        tipo_doc = doc.metadata.get("tipo_documento", "Sin tipo")
        
        # Aumentar a 350 caracteres para más información legal
        content = _truncate_text(doc.page_content, 350)
        
        # Formato más informativo con todos los metadatos
        header = f"**{i}.** Expediente: {exp}"
        if materia != "Sin especificar":
            header += f" | Materia: {materia}"
        if sede != "Sin sede":
            header += f" | Sede: {sede}"
        if fecha != "Sin fecha":
            header += f" | Fecha: {fecha}"
        if tipo_doc != "Sin tipo":
            header += f" | Tipo: {tipo_doc}"
            
        context_parts.append(f"{header}\n{content}")
    
    return "\n\n" + "─"*50 + "\n\n".join(context_parts)