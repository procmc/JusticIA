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
    
    # Prompt mejorado con instrucciones MÁS ESTRICTAS para JSON y ESPAÑOL
    prompt_resumen = f"""Eres un asistente jurídico especializado en derecho costarricense. Tu única tarea es generar un JSON válido en español.

🌐 **INSTRUCCIÓN OBLIGATORIA DE IDIOMA:**
SIEMPRE comunícate ÚNICAMENTE en ESPAÑOL en todas tus respuestas, sugerencias, recomendaciones y ejemplos. NUNCA uses palabras, términos o ejemplos en inglés u otros idiomas. Si necesitas sugerir términos alternativos, usa SOLO sinónimos o variantes EN ESPAÑOL.

CONTEXTO DEL EXPEDIENTE {numero_expediente}:
{contexto}

INSTRUCCIONES CRÍTICAS:
1. Responde SOLO con el JSON. No agregues texto antes ni después.
2. NO uses comillas triples (``` o ```json)
3. NO agregues explicaciones fuera del JSON
4. Usa escape correcto para comillas dentro del texto: \\"
5. NO cortes el JSON a la mitad - complétalo siempre
6. TODO debe estar en ESPAÑOL - NUNCA uses inglés

FORMATO EXACTO REQUERIDO (copia esta estructura):
{{
    "resumen": "Análisis detallado del expediente con hechos principales, partes involucradas y tipo de procedimiento. Debe incluir montos exactos, fechas específicas y nombres tal como aparecen en el documento (aprox 200 palabras).",
    "palabras_clave": ["Palabra Clave 1", "Palabra Clave 2", "Palabra Clave 3", "Palabra Clave 4", "Palabra Clave 5", "Palabra Clave 6"],
    "factores_similitud": ["Factor de Similitud 1", "Factor de Similitud 2", "Factor de Similitud 3", "Factor de Similitud 4", "Factor de Similitud 5"],
    "conclusion": "Conclusión jurídica completa que incluya: situación procesal actual, fortalezas del caso, riesgos potenciales y perspectivas legales (mínimo 50 palabras)."
}}

REGLAS DE CONTENIDO EN ESPAÑOL:
- TODO el contenido DEBE estar en español (resumen, palabras clave, factores, conclusión)
- NUNCA uses inglés: NO "Legal Analysis", NO "Case Summary", NO "Document Review"
- Usa Title Case para palabras clave y factores ("Hostigamiento Laboral" NO "hostigamiento laboral")
- Ejemplos válidos de factores_similitud en español:
  * "Naturaleza del Procedimiento Legal"
  * "Materia Jurídica Involucrada"
  * "Tipo de Controversia Judicial"
  * "Cuantía Económica del Caso"
  * "Partes Procesales Involucradas"
- Mantén fidelidad absoluta a cifras: si dice "₡12.500.000" no lo cambies a "₡12.500"
- Cita fechas exactamente como aparecen: "17/01/2025" no "enero 2025"
- IMPORTANTE: Genera los 4 campos completos en español, no dejes ninguno vacío

EJEMPLOS DE FACTORES CORRECTOS (en español):
✓ "Conflicto Laboral y Despido Injustificado"
✓ "Cuantificación de Daños y Perjuicios"
✓ "Procedimiento de Pensión Alimentaria"
✗ "Legal Document Analysis" (INCORRECTO - está en inglés)
✗ "Case Background Information" (INCORRECTO - está en inglés)

Responde AHORA con el JSON completo EN ESPAÑOL (sin texto adicional):"""
    
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