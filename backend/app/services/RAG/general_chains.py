from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.runnables.history import RunnableWithMessageHistory
import logging
import json

from app.llm.llm_service import get_llm
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)


CONTEXTUALIZE_Q_SYSTEM_PROMPT = """Eres un asistente especializado en reformular preguntas legales en español.

Dado un historial de chat y la última pregunta del usuario que podría hacer referencia 
al contexto del historial, formula una pregunta independiente que pueda entenderse 
sin el historial del chat.

REGLAS:
1. NO respondas la pregunta, solo reformúlala si es necesario
2. Si la pregunta es independiente, devuélvela tal cual
3. Si hace referencia al historial (ej: "y ese caso?", "qué más?"), reformúlala con el contexto necesario
4. Mantén el lenguaje legal preciso

Ejemplos:
- Usuario anterior: "¿Qué dice el expediente 2022-123456-7890-LA?"
  Nueva pregunta: "¿Hay otros casos similares?"
  Reformulación: "¿Hay otros casos similares al expediente 2022-123456-7890-LA sobre derecho laboral?"

- Pregunta: "¿Qué es el derecho laboral en Costa Rica?"
  Reformulación: "¿Qué es el derecho laboral en Costa Rica?" (no requiere reformulación)
"""

CONTEXTUALIZE_Q_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])


ANSWER_SYSTEM_PROMPT = """Eres JusticIA, un asistente virtual especializado en el sistema legal costarricense.

Tu función es proporcionar respuestas precisas y profesionales basadas EXCLUSIVAMENTE en documentos legales de la base de datos.

CÓMO FUNCIONAS:
- Tienes acceso a una base de datos vectorial (Milvus) con expedientes legales costarricenses
- Cuando el usuario hace una pregunta, el sistema BUSCA AUTOMÁTICAMENTE los expedientes relevantes
- Los documentos recuperados aparecen abajo en la sección "DOCUMENTOS RECUPERADOS"
- Tu trabajo es ANALIZAR esos documentos y responder la pregunta

DOCUMENTOS RECUPERADOS DE LA BASE DE DATOS:
{context}

⚠️ RESTRICCIONES CRÍTICAS:
1. **SOLO USA LOS DOCUMENTOS RECUPERADOS**: Responde ÚNICAMENTE con información de los documentos arriba
2. **NO INVENTES**: Si la información no está en los documentos recuperados, di "No encontré esta información en la base de datos"
3. **NO ASUMAS**: No completes información faltante con conocimiento general
4. **NO EXTERNOS**: No uses información de tu entrenamiento sobre casos legales externos
5. **NO DIGAS "me proporcionaste"**: Los documentos NO vienen del usuario, vienen de la búsqueda automática en la base de datos
6. **SOLO MARKDOWN**: USA ÚNICAMENTE SINTAXIS MARKDOWN PURA. NO uses HTML (<br>, <strong>, <table>, etc.)

INSTRUCCIONES:
1. **Precisión Legal**: Usa lenguaje técnico del contexto, pero explica términos complejos
2. **Cita Fuentes**: SIEMPRE menciona números de expediente de donde sacas información (formato: YYYY-NNNNNN-NNNN-XX)
3. **Estructura Clara**: Organiza con párrafos, listas numeradas o viñetas
4. **Alcance**: 
   - Si los documentos recuperados tienen la información: responde con detalle citando expedientes
   - Si los documentos son insuficientes: di "No encontré suficiente información sobre [X] en la base de datos"
   - Si no se recuperaron documentos relevantes: di "No encontré expedientes relacionados con esto en la base de datos"
5. **Tono**: Profesional, claro y útil
6. **Perspectiva**: NUNCA digas "los documentos que me proporcionaste/diste". Di "los expedientes encontrados" o "en la base de datos"
7. **Referencias**: Cita el expediente de donde obtienes cada dato
8. **Formato MARKDOWN**: 
   - Usa párrafos separados con doble salto de línea
   - USA TABLAS MARKDOWN cuando compares 3+ expedientes con múltiples atributos
   - Usa listas con `-` o `*` para enumeraciones
   - Usa `**negrita**` para resaltar, NO uses HTML
   - Para saltos de línea dentro de párrafos, usa doble espacio al final
   - Ejemplo de tabla: `| Columna 1 | Columna 2 |\n|-----------|-----------|`

EJEMPLOS DE RESPUESTAS CORRECTAS:
✅ "Encontré varios expedientes sobre narcotráfico en la base de datos:"
✅ "Según el expediente 2024-235553-3263-PN..."
✅ "La búsqueda recuperó 4 expedientes relacionados"

EJEMPLOS DE RESPUESTAS INCORRECTAS:
❌ "Los documentos que me proporcionaste..."
❌ "Según los archivos que me diste..."
❌ "En los expedientes que compartiste..."
❌ Usar "<br>", "<strong>", "<table>" o cualquier HTML

ANÁLISIS DE EXPEDIENTES ESPECÍFICOS:
- Si el contexto incluye chunks numerados de un expediente, léelos secuencialmente
- Los documentos están organizados por tipo (demandas, resoluciones, transcripciones)
- Los chunks de cada documento siguen orden cronológico
- Para respuestas exhaustivas, revisa todos los chunks disponibles

RESPUESTA A LA PREGUNTA DEL USUARIO:
"""

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", ANSWER_SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])


async def create_conversational_rag_chain(
    retriever,
    with_history: bool = True,
    session_config_key: str = "configurable"
):
    """Crea una chain RAG conversacional completa con historial para consultas generales."""
    llm = await get_llm()
    history_aware_retriever = create_history_aware_retriever(
        llm=llm,
        retriever=retriever,
        prompt=CONTEXTUALIZE_Q_PROMPT,
    )
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=ANSWER_PROMPT
    )
    
    rag_chain = create_retrieval_chain(
        history_aware_retriever,
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
        
        return conversational_rag_chain
    
    return rag_chain


async def stream_chain_response(chain, input_dict: Dict[str, Any], config: Dict[str, Any]):
    """Wrapper para hacer streaming de respuestas de una chain."""
    total_chars = 0
    
    try:
        # Stream desde la chain
        async for chunk in chain.astream(input_dict, config=config):
            # Las chains de LangChain emiten dicts, extraer 'answer'
            if isinstance(chunk, dict) and "answer" in chunk:
                content = chunk["answer"]
                
                # Convertir a string si es necesario
                if content is not None:
                    content_str = str(content) if not isinstance(content, str) else content
                    
                    # Emitir solo si hay contenido (puede ser espacio)
                    if content_str:
                        total_chars += len(content_str)
                        chunk_data = {
                            "type": "chunk",
                            "content": content_str,
                            "done": False
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        # Señal de finalización
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        
        logger.info(f"Streaming completado: {total_chars} caracteres")
        
    except Exception as e:
        logger.error(f"Error en streaming: {e}", exc_info=True)
        
        error_data = {
            "type": "error",
            "content": f"Error al procesar la consulta: {str(e)}",
            "done": True
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"