"""
Módulo para formateo de contexto y extracción de metadatos de documentos
"""
from typing import List, Dict, Any
from langchain_core.documents import Document


def format_documents_context_extended(docs: List[Document], max_docs: int = 5, use_full_chunks: bool = True) -> str:
    """
    Formateo EXTENDIDO que aprovecha al máximo el chunking del módulo de ingesta.
    Usa chunks completos de 7000 caracteres cada uno para evitar alucinaciones.
    
    Args:
        docs: Lista de documentos de LangChain (chunks de 7000 chars c/u)
        max_docs: Número máximo de chunks a incluir (5 = ~35,000 caracteres, balance óptimo)
        use_full_chunks: Si True, usa chunks completos sin truncar
    
    Returns:
        Contexto formateado con información completa de chunks
    """
    if not docs:
        return "No hay información disponible."
    
    context_parts = []
    docs_to_use = docs[:min(len(docs), max_docs)]
    
    total_chars = 0
    for i, doc in enumerate(docs_to_use, 1):
        # Extraer metadatos del chunk
        expediente = doc.metadata.get("numero_expediente", doc.metadata.get("expediente_numero", "Sin expediente"))
        archivo = doc.metadata.get("nombre_archivo", doc.metadata.get("archivo", "Sin archivo"))
        tipo_documento = doc.metadata.get("tipo_documento", "documento")
        indice_chunk = doc.metadata.get("indice_chunk", i-1)
        total_chunks = doc.metadata.get("meta", {}).get("total_chunks", "desconocido")
        pagina_inicio = doc.metadata.get("pagina_inicio", "N/A")
        pagina_fin = doc.metadata.get("pagina_fin", "N/A")
        chunk_length = doc.metadata.get("meta", {}).get("chunk_length", len(doc.page_content))
        relevancia = doc.metadata.get("relevance_score", 0)
        
        # Usar contenido completo del chunk (sin truncar)
        content = doc.page_content
        if not use_full_chunks and len(content) > 6000:
            # Solo truncar si se solicita explícitamente
            truncated = content[:6000]
            last_period = truncated.rfind('.')
            if last_period > 5500:
                content = truncated[:last_period + 1] + "...[TRUNCADO]"
            else:
                content = truncated + "...[TRUNCADO]"
        
        total_chars += len(content)
        
        context_parts.append(
            f"**📋 DOCUMENTO {i}/{len(docs_to_use)} - CHUNK {indice_chunk+1}/{total_chunks}**\n"
            f"🔢 Expediente: {expediente}\n"
            f"📄 Archivo: {archivo}\n"
            f"📑 Tipo: {tipo_documento}\n"
            f"📍 Páginas: {pagina_inicio}-{pagina_fin}\n"
            f"📊 Tamaño chunk: {chunk_length:,} caracteres\n"
            f"🎯 Relevancia: {relevancia:.3f}\n"
            f"📝 **CONTENIDO COMPLETO DEL CHUNK:**\n{content}\n"
        )
    
    header = f"**🔍 CONTEXTO EXTENDIDO - {len(docs_to_use)} CHUNKS ({total_chars:,} caracteres)**\n"
    separator = "\n" + "="*100 + "\n"
    
    return header + separator.join(context_parts) + separator

def calculate_optimal_retrieval_params(query_length: int, context_importance: str = "high") -> Dict[str, int]:
    """
    Calcula parámetros óptimos de recuperación basado en la consulta y importancia del contexto.
    
    Args:
        query_length: Longitud de la consulta en caracteres
        context_importance: "low", "medium", "high", "maximum"
    
    Returns:
        Dict con parámetros optimizados: top_k, max_docs_context, target_chars
    """
    # Configuraciones OPTIMIZADAS para mejor relevancia y menos ruido
    configs = {
        "low": {"base_top_k": 3, "max_docs": 3, "target_chars": 21000},      # Consultas muy específicas
        "medium": {"base_top_k": 4, "max_docs": 4, "target_chars": 28000},   # Consultas normales  
        "high": {"base_top_k": 5, "max_docs": 5, "target_chars": 35000},     # Consultas complejas
        "maximum": {"base_top_k": 6, "max_docs": 6, "target_chars": 42000}   # Análisis exhaustivo
    }
    
    config = configs.get(context_importance, configs["high"])
    
    # Ajustar top_k basado en longitud de consulta
    if query_length > 500:  # Consulta muy específica
        top_k = config["base_top_k"] + 2
    elif query_length > 200:  # Consulta detallada
        top_k = config["base_top_k"] + 1
    else:  # Consulta simple
        top_k = config["base_top_k"]
    
    return {
        "top_k": min(top_k, 15),  # Límite máximo
        "max_docs_context": config["max_docs"],
        "target_chars": config["target_chars"]
    }

def format_documents_context_adaptive(docs: List[Document], query: str = "", context_importance: str = "high") -> str:
    """
    Formateo adaptativo que ajusta automáticamente los parámetros según la consulta.
    Combina el chunking del módulo de ingesta con parámetros inteligentes.
    
    Args:
        docs: Lista de documentos de LangChain
        query: Consulta original (para ajustar parámetros)
        context_importance: Nivel de importancia del contexto
    
    Returns:
        Contexto formateado de manera óptima
    """
    if not docs:
        return "No hay información disponible."
    
    # Calcular parámetros óptimos
    params = calculate_optimal_retrieval_params(len(query), context_importance)
    
    # Usar formateo extendido con parámetros calculados
    return format_documents_context_extended(
        docs, 
        max_docs=params["max_docs_context"], 
        use_full_chunks=True
    )

def _truncate_text_smart(text: str, max_length: int) -> str:
    """
    Trunca texto de manera inteligente, respetando oraciones completas
    """
    if len(text) <= max_length:
        return text
    
    # Buscar el final de una oración cerca del límite
    truncated = text[:max_length]
    
    # Buscar punto, signo de exclamación o interrogación
    for punct in ['.', '!', '?']:
        last_punct = truncated.rfind(punct)
        if last_punct > max_length - 50:  # Si está cerca del final
            return truncated[:last_punct + 1] + "..."
    
    # Si no hay puntuación, buscar el final de una palabra
    last_space = truncated.rfind(' ')
    if last_space > max_length - 20:
        return truncated[:last_space] + "..."
    
    return truncated + "..."

    """
    Versión "compacta" pero con información sustancial para expedientes
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos a incluir (12 para información completa)
    
    Returns:
        Contexto con información detallada pero organizada
    """
    if not docs:
        return "Sin información de expedientes disponible."
    
    context_parts = []
    
    for i, doc in enumerate(docs[:max_docs], 1):
        exp = doc.metadata.get("expediente_numero", "N/A")
        materia = doc.metadata.get("materia", "Sin especificar")
        sede = doc.metadata.get("sede_judicial", "Sin sede")
        fecha = doc.metadata.get("fecha", "Sin fecha")
        tipo_doc = doc.metadata.get("tipo_documento", "Sin tipo")
        relevancia = doc.metadata.get("relevance_score", 0)
        
        # Aumentar SIGNIFICATIVAMENTE el contenido: 700 caracteres
        content = _truncate_text_smart(doc.page_content, 700)
        
        # Header más informativo
        header = f"**📋 EXPEDIENTE {i}: {exp}**"
        metadata_line = f"⚖️ {materia} | 🏛️ {sede} | 📅 {fecha} | 📄 {tipo_doc} | 🎯 Rel: {relevancia:.2f}"
        
        context_parts.append(f"{header}\n{metadata_line}\n\n📝 **Contenido Detallado:**\n{content}")
    
    return "\n\n" + "="*60 + "\n\n".join(context_parts) + "\n\n" + "="*60