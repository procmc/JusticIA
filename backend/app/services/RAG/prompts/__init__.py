"""
"""
Módulo de prompts del sistema RAG de JusticBot.

Consolidacada tipo de prompt de LangChain para el asistente virtual:
- Contextualización de preguntas con historial
- Generación de respuestas con fuentes
- Análisis de expedientes específicos
- Formateo de documentos

Prompts disponibles:
    * CONTEXTUALIZE_Q_PROMPT: Reformulación con expansión semántica
    * ANSWER_PROMPT: Generación de respuestas generales
    * DOCUMENT_PROMPT: Formateo de documentos individuales
    * get_expediente_prompt: Generador de prompts para expedientes

Arquitectura:
    Cada prompt está en su propio archivo para:
    - Facilitar mantenimiento y versioning
    - Permitir testing independiente
    - Mejorar legibilidad (prompts largos)
    - Separar responsabilidades

Uso en chains:
    * general_chains: CONTEXTUALIZE_Q_PROMPT + ANSWER_PROMPT
    * expediente_chains: get_expediente_prompt (sin contextualización)
    * formatted_retriever: DOCUMENT_PROMPT

Example:
    >>> from app.services.rag.prompts import ANSWER_PROMPT, get_expediente_prompt
    >>> 
    >>> # Prompt general
    >>> general_prompt = ANSWER_PROMPT
    >>> 
    >>> # Prompt de expediente
    >>> exp_prompt = get_expediente_prompt("24-000123-0001-PE")

Note:
    * Todos los prompts son ChatPromptTemplate de LangChain
    * Soportan MessagesPlaceholder para historial
    * DOCUMENT_PROMPT es PromptTemplate simple
    * get_expediente_prompt es función generadora, no prompt directo

Ver también:
    * app.services.rag.general_chains: Usa prompts generales
    * app.services.rag.expediente_chains: Usa prompt de expedientes

Authors:
    JusticIA Team

Version:
    3.0.0 - Sistema completo de prompts
"""
"""Módulo de prompts para el sistema RAG de JusticBot.
Cada tipo de prompt está en su propio archivo para facilitar el mantenimiento.
"""

from .contextualize_prompt import CONTEXTUALIZE_Q_PROMPT
from .answer_prompt import ANSWER_PROMPT, DOCUMENT_PROMPT
from .expediente_prompt import get_expediente_prompt

__all__ = [
    'CONTEXTUALIZE_Q_PROMPT',
    'ANSWER_PROMPT',
    'DOCUMENT_PROMPT',
    'get_expediente_prompt',
]
