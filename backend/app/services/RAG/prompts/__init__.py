"""Instrucciones de los chats de ServIA (spec 007): un texto plano por chat y uno de reformulación."""

from .contextualize_prompt import INSTRUCCION_REFORMULACION
from .answer_prompt import INSTRUCCIONES_GENERAL
from .expediente_prompt import instrucciones_tema
from .notebook_prompt import instrucciones_notebook

__all__ = [
    'INSTRUCCION_REFORMULACION',
    'INSTRUCCIONES_GENERAL',
    'instrucciones_tema',
    'instrucciones_notebook',
]
