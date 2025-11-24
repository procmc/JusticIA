"""
Constructor de Prompts Especializados para Búsqueda de Similares y Generación de Resúmenes.

Este módulo contiene funciones especializadas en la construcción de prompts
optimizados para el sistema de búsqueda de casos similares y generación de
resúmenes automáticos de expedientes judiciales con IA.

Responsabilidades:
    - Construir prompts para resúmenes de expedientes (create_similarity_summary_prompt)
    - Formatear contexto de documentos para búsquedas (create_similarity_search_context)
    - Aplicar mejores prácticas de prompt engineering para LLMs legales

Separación de responsabilidades:
    - Este módulo: Solo construcción de prompts (string templates)
    - SimilarityService: Orquestación y llamadas al LLM
    - ResponseParser: Parseo y validación de respuestas

Características del prompt de resumen:
    1. **Instrucción de idioma obligatoria**: TODO en español (Costa Rica)
    2. **Formato JSON estricto**: Sin markdown, sin texto adicional
    3. **Estructura fija**: resumen, palabras_clave, factores_similitud, conclusion
    4. **Ejemplos de factores**: Provee ejemplos válidos en español
    5. **Validación de contenido**: Reglas para mantener fidelidad a datos (fechas, montos)
    6. **Escape de caracteres**: Instrucciones para comillas y caracteres especiales
    7. **Longitud definida**: ~200 palabras resumen, mínimo 50 palabras conclusión

Prompt engineering aplicado:
    - Role prompting: "Eres un asistente jurídico especializado..."
    - Few-shot learning: Ejemplos de factores correctos vs incorrectos
    - Chain of thought: Instrucciones paso a paso
    - Format enforcement: Estructura JSON con campos explícitos
    - Constraint specification: Reglas de contenido claras

Formato de salida esperado (JSON):
    {
        "resumen": "Texto descriptivo del expediente...",
        "palabras_clave": ["Palabra 1", "Palabra 2", ...],
        "factores_similitud": ["Factor 1", "Factor 2", ...],
        "conclusion": "Análisis jurídico final..."
    }

Contexto de documentos:
    - Agrupa chunks por documento origen
    - Ordena chunks secuencialmente para coherencia
    - Limita longitud total (max_docs, max_chars_per_doc)
    - Preserva metadata relevante (número expediente, archivo)

Parámetros de configuración:
    - max_docs: 15 chunks totales (balance contexto/performance)
    - max_chars_per_doc: 7000 caracteres por chunk (documentos legales largos)

Problemas comunes resueltos:
    1. ❌ LLM responde en inglés → ✅ Instrucción de idioma explícita
    2. ❌ JSON con markdown → ✅ "NO uses comillas triples"
    3. ❌ JSON incompleto → ✅ "NO cortes el JSON a la mitad"
    4. ❌ Factores en inglés → ✅ Ejemplos correctos en español
    5. ❌ Escape incorrecto → ✅ Instrucciones de escape explícitas

Integration:
    - SimilarityService: Consume los prompts construidos
    - ResponseParser: Valida que el output cumpla el formato esperado
    - chunk_context_builder: Formatea documentos para contexto

Example:
    >>> prompt = create_similarity_summary_prompt(
    ...     contexto="Demanda por despido injustificado...",
    ...     numero_expediente="24-000123-0001-LA"
    ... )
    >>> print(len(prompt))
    2847  # Prompt completo con instrucciones
    >>> 
    >>> contexto = create_similarity_search_context(
    ...     docs=langchain_documents,
    ...     max_docs=15
    ... )
    >>> print("DOCUMENTO:" in contexto)
    True

Note:
    - Los prompts son independientes del sistema RAG general
    - El formato JSON debe ser parseado por ResponseParser
    - Los factores de similitud son términos legales en español (Title Case)
    - La fidelidad a datos es crítica (fechas, montos exactos)

Ver también:
    - app.services.busqueda_similares.similarity_service: Consumidor principal
    - app.services.busqueda_similares.response_parser: Validación de respuestas
    - app.services.RAG.chunk_context_builder: Formateo de documentos

Authors:
    Roger Calderón Urbina
    Yeslin Chinchilla Ruiz

Version:
    1.0.0
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