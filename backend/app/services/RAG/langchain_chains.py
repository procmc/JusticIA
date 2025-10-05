"""
LangChain Conversational Chains para JusticIA.

Implementa:
- create_history_aware_retriever: Reformulación automática de preguntas con contexto
- create_retrieval_chain: Chain principal que combina retriever + answer generation
- create_stuff_documents_chain: Chain para generar respuestas desde documentos

Compatible con streaming y gestión de sesiones.
"""

from typing import List, Dict, Any, Optional
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


# =====================================================================
# PROMPTS CONVERSACIONALES
# =====================================================================

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
8. **Formato**: 
   - Usa párrafos y listas para la mayoría de respuestas
   - USA TABLAS SOLO cuando compares 3+ expedientes con múltiples atributos
   - NO uses tablas para un solo expediente o respuestas narrativas
   - Prefiere listas con viñetas para enumeraciones simples

EJEMPLOS DE RESPUESTAS CORRECTAS:
✅ "Encontré varios expedientes sobre narcotráfico en la base de datos:"
✅ "Según el expediente 2024-235553-3263-PN..."
✅ "La búsqueda recuperó 4 expedientes relacionados"

EJEMPLOS DE RESPUESTAS INCORRECTAS:
❌ "Los documentos que me proporcionaste..."
❌ "Según los archivos que me diste..."
❌ "En los expedientes que compartiste..."

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


# =====================================================================
# FACTORIES PARA CREAR CHAINS
# =====================================================================

async def create_conversational_rag_chain(
    retriever,
    with_history: bool = True,
    session_config_key: str = "configurable"
):
    """
    Crea una chain RAG conversacional completa con historial.
    
    Esta es la chain principal que:
    1. Reformula la pregunta con contexto histórico (history_aware_retriever)
    2. Recupera documentos relevantes
    3. Genera respuesta basada en documentos + historial
    4. Gestiona sesiones automáticamente
    
    Args:
        retriever: LangChain retriever (ej: DynamicJusticIARetriever)
        with_history: Si True, habilita gestión de historial con sessions
        session_config_key: Clave de configuración para session_id
    
    Returns:
        Runnable chain lista para invocar con streaming
    
    Usage:
        chain = await create_conversational_rag_chain(retriever)
        
        # Con streaming
        async for chunk in chain.astream(
            {"input": "¿Qué es el derecho laboral?"},
            config={"configurable": {"session_id": "session_user_123"}}
        ):
            print(chunk)
    """
    llm = await get_llm()
    
    # 1. History-Aware Retriever: Reformula pregunta con contexto
    history_aware_retriever = create_history_aware_retriever(
        llm=llm,
        retriever=retriever,
        prompt=CONTEXTUALIZE_Q_PROMPT,
    )
    
    logger.info("✅ History-aware retriever creado")
    
    # 2. Document Chain: Genera respuesta desde documentos
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=ANSWER_PROMPT
    )
    
    logger.info("✅ Question-answer chain creado")
    
    # 3. Retrieval Chain: Combina retriever + answer generation
    rag_chain = create_retrieval_chain(
        history_aware_retriever,
        question_answer_chain,
    )
    
    logger.info("✅ RAG chain creado")
    
    # 4. Agregar gestión de historial si está habilitado
    if with_history:
        conversational_rag_chain = RunnableWithMessageHistory(
            rag_chain,
            get_session_history_func(),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        logger.info("✅ Chain conversacional con historial creado")
        return conversational_rag_chain
    
    return rag_chain


async def create_expediente_specific_chain(
    retriever,
    expediente_numero: str,
    with_history: bool = True
):
    """
    Crea una chain especializada para análisis de expediente específico.
    
    Similar a create_conversational_rag_chain pero con:
    - Prompt adaptado para análisis exhaustivo de expediente
    - Instrucciones para chunks secuenciales
    - Énfasis en estructura de documentos
    
    Args:
        retriever: Retriever configurado para el expediente específico
        expediente_numero: Número del expediente
        with_history: Si True, habilita gestión de historial
    
    Returns:
        Runnable chain especializada en expedientes
    """
    llm = await get_llm()
    
    # Prompt especializado para expedientes
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
✅ "Según los documentos del expediente {expediente_numero}..."
✅ "El expediente {expediente_numero} contiene..."
✅ "En el Chunk 3 del expediente se indica..."

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
    
    # Chain con prompt especializado
    # IMPORTANTE: Para expedientes específicos, NO reformulamos la pregunta
    # Esto evita que se pierda el foco en el expediente específico
    # El retriever ya está filtrado por expediente, la pregunta original es más precisa
    
    # Chain de documentos
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=EXPEDIENTE_PROMPT
    )
    
    # Usamos retriever directo sin reformulación
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
        
        logger.info(f"✅ Chain expediente {expediente_numero} con historial creado")
        return conversational_rag_chain
    
    logger.info(f"✅ Chain expediente {expediente_numero} creado")
    return rag_chain


# =====================================================================
# UTILIDADES PARA STREAMING
# =====================================================================

async def stream_chain_response(chain, input_dict: Dict[str, Any], config: Dict[str, Any]):
    """
    Wrapper para hacer streaming de respuestas de una chain.
    
    Extrae solo el contenido de la respuesta ('answer') y lo emite chunk por chunk.
    Compatible con el formato SSE esperado por el frontend.
    
    Args:
        chain: LangChain Runnable chain
        input_dict: Dict con input para la chain (debe incluir 'input' key)
        config: Dict de configuración (debe incluir 'configurable': {'session_id': ...})
    
    Yields:
        str: Chunks de respuesta en formato SSE
    
    Usage:
        async for chunk in stream_chain_response(
            chain,
            {"input": "pregunta"},
            {"configurable": {"session_id": "session_123"}}
        ):
            # chunk es string SSE listo para enviar
            yield chunk
    """
    import json
    
    print(f"\n{'='*80}")
    print(f"🎬 STREAMING - Iniciando streaming de respuesta")
    print(f"   - Input: {input_dict.get('input', 'N/A')[:100]}...")
    print(f"   - Session ID: {config.get('configurable', {}).get('session_id', 'N/A')}")
    print(f"{'='*80}\n")
    
    chunk_count = 0
    total_chars = 0
    
    try:
        # Stream desde la chain
        async for chunk in chain.astream(input_dict, config=config):
            chunk_count += 1
            
            # Debug primer chunk
            if chunk_count == 1:
                print(f"📦 Primer chunk - Tipo: {type(chunk)}, Keys: {list(chunk.keys()) if isinstance(chunk, dict) else 'N/A'}")
            
            # Las chains de LangChain emiten dicts, extraer 'answer'
            if isinstance(chunk, dict):
                if "answer" in chunk:
                    content = chunk["answer"]
                    
                    if content:  # Solo emitir si hay contenido
                        total_chars += len(str(content))
                        chunk_data = {
                            "type": "chunk",
                            "content": str(content),
                            "done": False
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    else:
                        print(f"⚠️  Chunk #{chunk_count} con 'answer' vacío")
                else:
                    print(f"⚠️  Chunk #{chunk_count} sin 'answer'. Keys: {list(chunk.keys())}")
        
        # Señal de finalización
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        
        print(f"\n{'='*80}")
        print(f"✅ STREAMING COMPLETADO")
        print(f"   - Total chunks: {chunk_count}")
        print(f"   - Total caracteres: {total_chars}")
        if total_chars == 0:
            print(f"   ⚠️  ADVERTENCIA: No se generó contenido!")
        print(f"{'='*80}\n")
        
        logger.info("✅ Streaming completado exitosamente")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ ERROR EN STREAMING: {e}")
        print(f"{'='*80}\n")
        
        logger.error(f"❌ Error en streaming: {e}", exc_info=True)
        
        error_data = {
            "type": "error",
            "content": f"Error al procesar la consulta: {str(e)}",
            "done": True
        }
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
