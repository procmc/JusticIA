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


def format_documents_context(docs: List[Document], max_docs: int = 15, max_chars_per_doc: int = 1000) -> str:
    """
    Formatea documentos para el contexto del LLM - Optimizado para información detallada de expedientes
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos a incluir (15 para análisis completo)
        max_chars_per_doc: Caracteres máximos por documento (1000 para información muy detallada)
    
    Returns:
        Contexto formateado como string con información completa
    """
    if not docs:
        return "No hay información disponible."
    
    context_parts = []
    # Aumentar documentos para análisis más completo
    docs_to_use = docs[:min(len(docs), max_docs)]
    
    for i, doc in enumerate(docs_to_use, 1):
        expediente = doc.metadata.get("expediente_numero", "Sin expediente")
        archivo = doc.metadata.get("archivo", "Sin archivo")
        materia = doc.metadata.get("materia", "Sin especificar")
        sede_judicial = doc.metadata.get("sede_judicial", "Sin sede")
        fecha = doc.metadata.get("fecha", "Sin fecha")
        tipo_documento = doc.metadata.get("tipo_documento", "Sin tipo")
        relevancia = doc.metadata.get("relevance_score", 0)
        
        # MÁS contenido para información MUY detallada
        content = doc.page_content
        if len(content) > max_chars_per_doc:
            # Truncar de manera inteligente, buscando el final de una oración
            truncated = content[:max_chars_per_doc]
            last_period = truncated.rfind('.')
            if last_period > max_chars_per_doc - 150:  # Buscar más lejos para más contenido
                content = truncated[:last_period + 1] + "..."
            else:
                content = truncated + "..."
        
        context_parts.append(
            f"**📋 EXPEDIENTE {i} - INFORMACIÓN COMPLETA**\n"
            f"🔢 Número de Expediente: {expediente}\n"
            f"⚖️ Materia Judicial: {materia}\n"
            f"🏛️ Sede Judicial: {sede_judicial}\n"
            f"📄 Tipo de Documento: {tipo_documento}\n"
            f"📅 Fecha: {fecha}\n"
            f"📁 Archivo Fuente: {archivo}\n"
            
            f"🎯 Relevancia: {relevancia:.2f}\n"
            f"📝 **CONTENIDO DETALLADO:**\n{content}\n"
        )
    
    return "\n" + "="*80 + "\n".join(context_parts) + "\n" + "="*80

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


def extract_document_sources(docs: List[Document]) -> List[Dict[str, Any]]:
    """
    Extrae información completa de fuentes para referencias detalladas
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
            "fragmento_completo": _truncate_text_smart(doc.page_content, 1000),  # MÁS información
            "resumen": _extract_summary(doc.page_content),  # Nuevo: resumen inteligente
            "palabras_clave": _extract_keywords(doc.page_content)  # Nuevo: palabras clave
        }
        fuentes.append(fuente)
    return fuentes

# Función para detectar solicitudes de más información
def should_use_detailed_format(query: str) -> bool:
    """
    Detecta si la consulta solicita información detallada
    """
    detailed_keywords = [
        'más información', 'mas información', 'más detalles', 'mas detalles',
        'qué más', 'que mas', 'información adicional', 'detalles adicionales',
        'profundizar', 'ampliar', 'extender', 'completo', 'detallado',
        'todo lo que sabes', 'toda la información', 'información completa',
        'más datos', 'mas datos', 'información específica', 'específico', 'detalladamente',
        'en detalle', 'desglosar', 'desglose', 'pormenores', 'pormenorizado','general'
    ]
    
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in detailed_keywords)

# Función inteligente que selecciona el formato según la consulta
def format_context_intelligent(docs: List[Document], query: str = "") -> str:
    """
    Selecciona automáticamente el formato más apropiado según la consulta
    """
    if should_use_detailed_format(query):
        # Usar formato MUY detallado para solicitudes específicas
        return format_documents_context(docs, max_docs=15, max_chars_per_doc=1500)
    elif len(docs) <= 5:
        # Para pocos documentos, mostrar todo el contenido
        return format_documents_context(docs, max_docs=5, max_chars_per_doc=2000)
    else:
        # Formato estándar pero generoso
        return format_context_compact(docs, max_docs=12)

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

def _extract_summary(text: str) -> str:
    """
    Extrae un resumen de las primeras líneas del documento
    """
    lines = text.split('\n')
    summary_lines = []
    char_count = 0
    
    for line in lines[:5]:  # Primeras 5 líneas
        if char_count + len(line) > 200:
            break
        summary_lines.append(line.strip())
        char_count += len(line)
    
    return ' '.join(summary_lines)

def _extract_keywords(text: str) -> List[str]:
    """
    Extrae palabras clave relevantes del texto
    """
    # Palabras clave comunes en documentos judiciales
    judicial_terms = [
        'demanda', 'sentencia', 'recurso', 'apelación', 'casación',
        'amparo', 'constitucional', 'civil', 'penal', 'laboral',
        'contencioso', 'administrativo', 'familia', 'violencia',
        'alimentos', 'divorcio', 'custodia', 'pensión'
    ]
    
    text_lower = text.lower()
    found_keywords = []
    
    for term in judicial_terms:
        if term in text_lower:
            found_keywords.append(term)
    
    return found_keywords[:5]  # Máximo 5 palabras clave

# Nueva función para información específica de expedientes
def format_expediente_detailed(docs: List[Document], expediente_numero: str = "") -> str:
    """
    Formato específico para cuando se solicita información detallada de expedientes
    """
    if not docs:
        return "No se encontró información para el expediente solicitado."
    
    # Filtrar por expediente específico si se proporciona
    if expediente_numero:
        docs = [doc for doc in docs if doc.metadata.get("expediente_numero") == expediente_numero]
    
    if not docs:
        return f"No se encontró información para el expediente {expediente_numero}."
    
    result = "🔍 **INFORMACIÓN DETALLADA DEL EXPEDIENTE**\n\n"
    
    for i, doc in enumerate(docs, 1):
        exp = doc.metadata.get("expediente_numero", "N/A")
        result += f"📋 **EXPEDIENTE: {exp}**\n"
        result += f"⚖️ Materia: {doc.metadata.get('materia', 'Sin especificar')}\n"
        result += f"🏛️ Sede: {doc.metadata.get('sede_judicial', 'Sin especificar')}\n"
        result += f"📅 Fecha: {doc.metadata.get('fecha', 'Sin especificar')}\n"
        result += f"📄 Tipo: {doc.metadata.get('tipo_documento', 'Sin especificar')}\n"
        result += f"📁 Archivo: {doc.metadata.get('archivo', 'Sin especificar')}\n\n"
        result += f"📝 **CONTENIDO COMPLETO:**\n{doc.page_content}\n"
        result += "\n" + "─"*80 + "\n\n"
    
    return result

# Funciones optimizadas para velocidad
def format_documents_context_fast(docs: List[Document], max_docs: int = 8, max_chars_per_doc: int = 400) -> str:
    """
    Formatea documentos para el contexto del LLM - OPTIMIZADO PARA VELOCIDAD
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos (8 para velocidad óptima)
        max_chars_per_doc: Caracteres máximos por documento (400 para respuesta rápida)
    
    Returns:
        Contexto formateado optimizado para velocidad
    """
    if not docs:
        return "No hay información disponible."
    
    context_parts = []
    # REDUCIDO: Máximo 8 documentos para velocidad
    docs_to_use = docs[:min(len(docs), max_docs)]
    
    for i, doc in enumerate(docs_to_use, 1):
        expediente = doc.metadata.get("expediente_numero", "N/A")
        materia = doc.metadata.get("materia", "")
        sede_judicial = doc.metadata.get("sede_judicial", "")
        
        # REDUCIDO: 400 caracteres máximo para velocidad
        content = _truncate_text_fast(doc.page_content, max_chars_per_doc)
        
        # Formato más compacto
        header = f"**Doc {i}** - Exp: {expediente}"
        if materia:
            header += f" ({materia})"
        if sede_judicial:
            header += f" - {sede_judicial}"
            
        context_parts.append(f"{header}\n{content}")
    
    return "\n" + "─"*40 + "\n".join(context_parts)

def format_context_compact_fast(docs: List[Document], max_docs: int = 5) -> str:
    """
    Versión ultra-compacta para máxima velocidad
    
    Args:
        docs: Lista de documentos de LangChain
        max_docs: Número máximo de documentos (5 para velocidad máxima)
    
    Returns:
        Contexto ultra-compacto
    """
    if not docs:
        return "Sin información."
    
    context_parts = []
    
    for i, doc in enumerate(docs[:max_docs], 1):
        exp = doc.metadata.get("expediente_numero", "N/A")
        materia = doc.metadata.get("materia", "")
        
        # ULTRA-COMPACTO: Solo 200 caracteres
        content = _truncate_text_fast(doc.page_content, 200)
        
        # Formato mínimo
        context_parts.append(f"**{i}.** {exp} ({materia}): {content}")
    
    return "\n\n".join(context_parts)

def _truncate_text_fast(text: str, max_length: int) -> str:
    """
    Truncado ultra-rápido sin buscar puntuación (para velocidad)
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def extract_document_sources_fast(docs: List[Document]) -> List[Dict[str, Any]]:
    """
    Extracción optimizada para velocidad
    """
    fuentes = []
    # LÍMITE: Solo primeros 5 documentos para velocidad
    for doc in docs[:5]:
        fuente = {
            "expediente": doc.metadata.get("expediente_numero", ""),
            "materia": doc.metadata.get("materia", ""),
            "sede_judicial": doc.metadata.get("sede_judicial", ""),
            "relevancia": doc.metadata.get("relevance_score", 0),
            "fragmento": _truncate_text_fast(doc.page_content, 150)  # MUY REDUCIDO
        }
        fuentes.append(fuente)
    return fuentes

def format_context_compact(docs: List[Document], max_docs: int = 12) -> str:
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