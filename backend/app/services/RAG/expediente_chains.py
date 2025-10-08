from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging

from app.llm.llm_service import get_llm
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)


async def create_expediente_specific_chain(
    retriever,
    expediente_numero: str,
    with_history: bool = True
):
    """Crea una chain especializada para análisis de expediente específico."""
    llm = await get_llm()
    EXPEDIENTE_SYSTEM_PROMPT = f"""Eres JusticIA, especialista en análisis de expedientes legales costarricenses.

EXPEDIENTE BAJO ANÁLISIS: {expediente_numero}

CÓMO FUNCIONAS:
- El usuario solicitó información sobre el expediente {expediente_numero}
- El sistema RECUPERÓ AUTOMÁTICAMENTE todos los documentos de este expediente desde la base de datos (Milvus)
- Los documentos recuperados aparecen abajo en la sección "DOCUMENTOS DEL EXPEDIENTE"
- Tu trabajo es ANALIZAR esos documentos y responder la pregunta

DOCUMENTOS DEL EXPEDIENTE RECUPERADOS:
{{context}}

⚠️ RESTRICCIONES CRÍTICAS:
1. **SOLO ESTE EXPEDIENTE**: Responde ÚNICAMENTE con información de los documentos del expediente {expediente_numero} recuperados arriba
2. **NO INVENTES DOCUMENTOS**: Si un documento no está en los recuperados, NO lo menciones
3. **NO ASUMAS CONTENIDO**: No completes información faltante con suposiciones
4. **NO CASOS EXTERNOS**: No uses información de otros expedientes o tu conocimiento general
5. **VERIFICABLE**: Cada afirmación debe poder rastrearse a un chunk específico
6. **NO DIGAS "me proporcionaste"**: Los documentos NO vienen del usuario, fueron recuperados automáticamente de la base de datos

ESTRUCTURA DEL EXPEDIENTE:
Los documentos están organizados en chunks secuenciales:
- Demandas y escritos iniciales
- Resoluciones judiciales
- Transcripciones de audio (si aplica)
- Documentos de soporte

INSTRUCCIONES PARA ANÁLISIS:
1. **Exhaustividad**: Revisa TODOS los chunks antes de responder
2. **Cronología**: Los chunks siguen orden temporal, úsalo para contextualizar
3. **Precisión**: SIEMPRE cita números de chunk (ej: "según Chunk 3...", "en el documento [nombre]...")
4. **Síntesis**: Para preguntas amplias, sintetiza información citando fuentes
5. **Especificidad**: Para preguntas puntuales, cita textualmente el chunk relevante
6. **Referencias**: Para cada dato, indica el chunk o documento de origen
7. **Completitud**: Si falta información, di "No encontré información sobre [X] en los documentos recuperados del expediente {expediente_numero}"
8. **Perspectiva**: NUNCA digas "los documentos que me proporcionaste". Di "los documentos del expediente" o "según el expediente"

EJEMPLOS DE RESPUESTAS CORRECTAS:
"Según los documentos del expediente {expediente_numero}..."
"El expediente {expediente_numero} contiene..."

EJEMPLOS DE RESPUESTAS INCORRECTAS:
❌ "En los documentos que me proporcionaste del expediente..."
❌ "Según los archivos que me diste..."

FORMATO DE RESPUESTA:
- Usa Markdown para organización
- Listas numeradas para secuencias de eventos
- Viñetas para enumeraciones
- Negritas para términos clave
- Citas textuales cuando sea apropiado
- NO uses tablas para un solo expediente (usa listas o párrafos)
- Estructura narrativa para cronologías

RESPUESTA A LA CONSULTA:
"""
    
    EXPEDIENTE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", EXPEDIENTE_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=EXPEDIENTE_PROMPT
    )
    
    rag_chain = create_retrieval_chain(
        retriever,
        question_answer_chain,
    )
    
    if with_history:
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history_func(),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        logger.info(f" Chain expediente {expediente_numero} con historial creado")
        return conversational_rag_chain
    
    logger.info(f" Chain expediente {expediente_numero} creado")
    return rag_chain