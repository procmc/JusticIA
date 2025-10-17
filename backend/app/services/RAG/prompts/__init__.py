"""
Módulo de prompts para el sistema RAG de JusticBot.
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
