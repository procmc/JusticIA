"""
Constructor de prompts específicos para servicios de similitud y resúmenes.
Separado del servicio principal para mejor organización y mantenimiento.
"""

from app.services.RAG.prompt_builder import create_justicia_prompt


def create_similarity_summary_prompt(contexto: str, numero_expediente: str) -> str:
    """
    Construye prompt especializado para resúmenes de expedientes legales.
    
    Args:
        contexto: Contexto de documentos formateado
        numero_expediente: Número del expediente a resumir
        
    Returns:
        Prompt completo optimizado para resúmenes legales en español
    """
    pregunta = f"Genera un resumen estructurado completo del expediente {numero_expediente}"
    
    # Usar create_justicia_prompt como base
    prompt_base = create_justicia_prompt(
        pregunta=pregunta,
        context=contexto,
        conversation_context=""
    )
    
    # Agregar instrucciones específicas para resúmenes legales
    prompt_resumen = prompt_base + """

INSTRUCCIONES ESPECÍFICAS PARA RESUMEN LEGAL:

Debes responder ÚNICAMENTE en ESPAÑOL y en formato JSON válido exacto:

{
    "resumen": "Descripción detallada del caso legal, incluyendo hechos principales, partes involucradas, tipo de procedimiento, estado procesal y aspectos jurídicos relevantes",
    "palabras_clave": ["término legal 1", "término legal 2", "término legal 3", "término legal 4", "término legal 5", "término legal 6"],
    "factores_similitud": ["Factor jurídico 1", "Factor procesal 2", "Factor doctrinal 3", "Factor legal 4", "Factor procesal 5"],
    "conclusion": "Análisis jurídico de las perspectivas del caso, fortalezas legales, debilidades procesales y conclusiones profesionales"
}

REGLAS ESPECÍFICAS PARA DOCUMENTOS LEGALES:
- El resumen debe ser detallado y profesional (máximo 400 palabras para casos complejos)
- Las palabras clave deben incluir términos jurídicos específicos, tipos procesales, y conceptos legales relevantes (6-8 palabras)
- Los factores de similitud deben identificar elementos jurídicos únicos: tipo de proceso, materias legales, precedentes aplicables, etc.
- La conclusión debe incluir análisis jurídico profesional sobre viabilidad, riesgos procesales y perspectivas legales
- Identifica claramente: tipo de proceso (PN, CV, AM, etc.), materias jurídicas involucradas, y estatus procesal
- SIEMPRE responde en ESPAÑOL - nunca en inglés ni otros idiomas
- Responde ÚNICAMENTE con el JSON, sin texto adicional antes o después"""

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