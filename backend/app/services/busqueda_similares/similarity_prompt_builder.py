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

REGLAS ESPECÍFICAS:
- El resumen debe incluir hechos principales, partes involucradas, tipo de procedimiento (máximo 200 palabras)
- 6 palabras clave específicas del ámbito jurídico costarricense
- 5 factores de similitud relevantes para encontrar casos similares
- La conclusión DEBE ser un análisis jurídico detallado que incluya: situación procesal actual, fortalezas del caso, posibles riesgos, y perspectivas legales (mínimo 50 palabras)
- Todo en español, respuesta SOLO en JSON válido"""

    return prompt_resumen


def create_similarity_search_context(docs, max_docs: int = 15, max_chars_per_doc: int = 800) -> str:
    """
    Formatea contexto optimizado para documentos legales en búsquedas de similitud.
    
    Args:
        docs: Lista de documentos LangChain
        max_docs: Máximo número de documentos (15 para casos legales)
        max_chars_per_doc: Máximo caracteres por documento (800 para documentos legales)
        
    Returns:
        Contexto formateado específicamente para documentos legales
    """
    from app.services.RAG.context_formatter import format_documents_context
    
    # Usar configuración optimizada para documentos legales
    return format_documents_context(
        docs=docs,
        max_docs=max_docs,
        max_chars_per_doc=max_chars_per_doc
    )