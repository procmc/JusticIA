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
    
    # Prompt completamente independiente sin usar create_justicia_prompt
    prompt_resumen = f"""Eres un especialista en análisis de expedientes legales de Costa Rica.

CONTEXTO DEL EXPEDIENTE:
{contexto}

EXPEDIENTE A ANALIZAR: {numero_expediente}

Tu tarea es analizar el expediente legal y generar un resumen estructurado en formato JSON.

Responde ÚNICAMENTE con un JSON válido con esta estructura exacta:

{{
    "resumen": "Descripción completa del caso",
    "palabras_clave": ["palabra1", "palabra2", "palabra3", "palabra4", "palabra5", "palabra6"],
    "factores_similitud": ["factor1", "factor2", "factor3", "factor4", "factor5"],
    "conclusion": "Análisis jurídico completo del expediente"
}}

INSTRUCCIONES IMPORTANTES:

**Sobre el contenido:**
- Analiza los hechos principales, partes involucradas y tipo de procedimiento en un resumen de aproximadamente 200 palabras
- Mantén TOTAL FIDELIDAD a los datos del contexto: montos, fechas, nombres y cifras deben citarse exactamente como aparecen
- Si el documento indica "₡12.500.000", reprodúcelo así (no lo simplifiques a "₡12.500")
- Si menciona "4 años" o fechas específicas (17/01/2025), cópialas literalmente
- No agregues información que no esté explícitamente en el contexto

**Sobre el formato de respuesta:**
- Identifica 6 palabras clave del ámbito jurídico costarricense con formato Title Case ("Hostigamiento Laboral", "Terminación Sin Causa Objetiva")
- Determina 5 factores de similitud para encontrar casos comparables, también en Title Case ("Casos De Hostigamiento Laboral")
- Desarrolla una conclusión jurídica completa que incluya situación procesal actual, fortalezas del caso, riesgos potenciales y perspectivas legales (mínimo 50 palabras)
- Responde únicamente con JSON válido en español"""

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