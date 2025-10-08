"""
Constructor de prompts específicos para servicios de similitud y resúmenes.
Separado del servicio principal para mejor organización y mantenimiento.
"""


def create_similarity_summary_prompt(contexto: str, numero_expediente: str) -> str:
    """
    Construye prompt especializado para resúmenes de expedientes legales.
    INDEPENDIENTE del sistema RAG para evitar interferencias de formato.
    
    Args:
        contexto: Contexto de documentos formateado
        numero_expediente: Número del expediente a resumir
        
    Returns:
        Prompt completo optimizado para resúmenes legales en español
    """
    
    # Prompt mejorado con instrucciones más estrictas para JSON
    prompt_resumen = f"""Eres un asistente de análisis legal especializado. Tu única tarea es generar un JSON válido.

CONTEXTO DEL EXPEDIENTE {numero_expediente}:
{contexto}

INSTRUCCIONES CRÍTICAS:
1. Responde SOLO con el JSON. No agregues texto antes ni después.
2. NO uses comillas triples (``` o ```json)
3. NO agregues explicaciones fuera del JSON
4. Usa escape correcto para comillas dentro del texto: \\"
5. NO cortes el JSON a la mitad - complétalo siempre

FORMATO EXACTO REQUERIDO (copia esta estructura):
{{
    "resumen": "Análisis detallado del expediente con hechos principales, partes involucradas y tipo de procedimiento. Debe incluir montos exactos, fechas específicas y nombres tal como aparecen en el documento (aprox 200 palabras).",
    "palabras_clave": ["Palabra Clave 1", "Palabra Clave 2", "Palabra Clave 3", "Palabra Clave 4", "Palabra Clave 5", "Palabra Clave 6"],
    "factores_similitud": ["Factor de Similitud 1", "Factor de Similitud 2", "Factor de Similitud 3", "Factor de Similitud 4", "Factor de Similitud 5"],
    "conclusion": "Conclusión jurídica completa que incluya: situación procesal actual, fortalezas del caso, riesgos potenciales y perspectivas legales (mínimo 50 palabras)."
}}

REGLAS DE CONTENIDO:
- Usa Title Case para palabras clave y factores ("Hostigamiento Laboral" NO "hostigamiento laboral")
- Mantén fidelidad absoluta a cifras: si dice "₡12.500.000" no lo cambies a "₡12.500"
- Cita fechas exactamente como aparecen: "17/01/2025" no "enero 2025"
- IMPORTANTE: Genera los 4 campos completos, no dejes ninguno vacío

Responde AHORA con el JSON completo (sin texto adicional):"""
    
    return prompt_resumen


def create_similarity_search_context(docs, max_docs: int = 15, max_chars_per_doc: int = 7000) -> str:
    """
    Formatea contexto optimizado para documentos legales en búsquedas de similitud.
    Agrupa por documento y ordena chunks para dar coherencia al LLM.
    
    Args:
        docs: Lista de documentos LangChain con metadata de Milvus
        max_docs: Máximo número de chunks totales (15-20 para casos legales)
        max_chars_per_doc: Máximo caracteres por chunk individual (800 para documentos legales)
        
    Returns:
        Contexto formateado estructurado por documentos y chunks ordenados
    """
    from app.services.RAG.chunk_context_builder import format_documents_by_chunks
    
    # Usar función especializada que agrupa por documento y ordena chunks
    return format_documents_by_chunks(
        docs=docs,
        max_docs=max_docs,
        max_chars_per_chunk=max_chars_per_doc
    )