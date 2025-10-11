from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
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
from .formatted_retriever import FormattedRetriever

logger = logging.getLogger(__name__)


CONTEXTUALIZE_Q_SYSTEM_PROMPT = """Eres JusticBot, experto en reformular preguntas legales para búsqueda vectorial en expedientes judiciales costarricenses.

Tu misión es transformar cada pregunta en una consulta ENRIQUECIDA que maximice la recuperación de documentos relevantes.

ESTRATEGIA DE EXPANSIÓN SEMÁNTICA:

1. **IDENTIFICAR TÉRMINOS LEGALES CLAVE** y agregar sus SINÓNIMOS/VARIANTES:
   - "prescripción" → incluir: caducidad, extinción de acción, pérdida del derecho
   - "embargo" → incluir: medida cautelar, traba de bienes, aseguramiento patrimonial
   - "despido" → incluir: cesantía, terminación laboral, desvinculación, cese
   - "pensión alimentaria" → incluir: obligación alimentaria, cuota alimenticia, manutención
   - "fraude" → incluir: estafa, engaño, delito económico, falsedad
   - "competencia" → incluir: jurisdicción, potestad, atribución del tribunal

2. **EXPANDIR CON TÉRMINOS RELACIONADOS DEL ÁREA LEGAL**:
   - Derecho Laboral: contratos, Código de Trabajo, relación laboral, derechos laborales
   - Derecho Penal: delito, imputado, fiscal, pena, sentencia condenatoria
   - Derecho Civil: demanda, actor, demandado, responsabilidad civil
   - Derecho Familia: divorcio, custodia, régimen patrimonial, alimentos
   - Derecho Administrativo: recurso, acto administrativo, procedimiento

3. **INCLUIR ARTÍCULOS Y NORMATIVA**:
   - Si menciona "artículo X" → agregar: "art. X", "artículo X", "numeral X"
   - Agregar códigos relevantes: Código Civil, CPC, Código Penal, Código Familia

4. **AGREGAR CONTEXTO JURISDICCIONAL**:
   - "expedientes costarricenses", "jurisprudencia Costa Rica", "tribunales costarricenses"

5. **PREGUNTAS META** (NO reformular):
   - Saludos: "hola", "buenos días"
   - Sistema: "¿cómo te llamas?", "¿qué puedes hacer?"

6. **REFERENCIAS POSICIONALES AL HISTORIAL** (CRÍTICO - reformular CON contexto):
   - Referencias numéricas: "el primer expediente", "el segundo caso", "el tercero", "el último"
   - Referencias deícticas: "ese caso", "ese expediente", "esa resolución", "aquel documento"
   - Referencias de continuidad: "¿qué más?", "explícame mejor", "dame más detalles", "amplía eso"
   - Pronombres: "¿cuál es su fecha?", "¿dónde dice eso?", "¿cómo terminó?"
   - Acción: INCLUIR el expediente/caso específico del historial según la posición mencionada
   - Ejemplo: Si la respuesta anterior mencionó 3 expedientes y preguntan "dame detalles del primer expediente", incluir el número exacto del primer expediente mencionado

7. **CAMBIOS DE CONTEXTO** (reformular SIN historial):
   - Si la nueva pregunta cambia COMPLETAMENTE de tema Y no tiene referencias → ignorar historial
   - Ejemplo: Si hablaban de laboral y preguntan sobre penal SIN referencias → nueva consulta independiente
   - Detectar cambios: palabras clave muy diferentes, materia legal distinta, SIN pronombres/referencias
   - IMPORTANTE: Si hay referencias ("ese", "el primero", "aquél") → SIEMPRE incluir historial aunque cambie el tema

EJEMPLOS DE EXPANSIÓN:

Pregunta original: "¿Aplicación del artículo 8.4 CPC?"
Reformulación expandida: "¿Aplicación interpretación del artículo 8.4 CPC art 8.4 Código Procesal Civil competencia jurisdicción tribunal arbitral medidas cautelares en expedientes judiciales costarricenses?"

Pregunta original: "¿Casos de despido injustificado?"
Reformulación expandida: "¿Expedientes judiciales sobre despido injustificado cesantía sin justa causa terminación laboral despido ilegal Código de Trabajo derechos laborales indemnización en Costa Rica?"

Pregunta original: "¿Qué es la prescripción?"
Reformulación expandida: "¿Qué es la prescripción caducidad extinción de la acción pérdida del derecho prescripción adquisitiva prescripción extintiva según jurisprudencia expedientes costarricenses?"

Historial: "¿Expedientes sobre narcotráfico?"
Nueva pregunta: "¿Y qué dice el artículo 169?"
Reformulación: "¿Qué dice el artículo 169 art 169 en expedientes sobre narcotráfico tráfico de drogas estupefacientes delitos contra la salud pública en Costa Rica?"

Historial con respuesta: "Encontré 3 expedientes sobre artículo 8.4 CPC: 19-000334-0642-CI, 22-000191-0386-CI, 2023-098908-1589-FA"
Nueva pregunta: "Dame más detalles del primer expediente"
Reformulación: "¿Qué más información hay sobre el expediente 19-000334-0642-CI relacionado con el artículo 8.4 CPC Código Procesal Civil competencia jurisdicción?"

Historial con respuesta: "El expediente 2022-123456-7890-LA trata sobre despido injustificado..."
Nueva pregunta: "¿Cuál fue la resolución de ese caso?"
Reformulación: "¿Cuál fue la resolución decisión fallo sentencia del expediente 2022-123456-7890-LA sobre despido injustificado cesantía terminación laboral?"

Historial: "¿Casos de despido laboral?"
Nueva pregunta: "¿Tienes info sobre fraude?" (CAMBIO DE CONTEXTO SIN REFERENCIAS)
Reformulación: "¿Expedientes judiciales sobre fraude estafa engaño delito económico falsedad delitos patrimoniales en Costa Rica?" (SIN historial laboral)

REGLAS CRÍTICAS:
- SIEMPRE expande con 3-5 sinónimos/términos relacionados
- NO inventes información del historial
- Si cambio de tema (laboral→penal, civil→familia) → ignora historial
- Primera pregunta de la conversación → máxima expansión semántica
- Mantén lenguaje legal preciso
"""

CONTEXTUALIZE_Q_PROMPT = ChatPromptTemplate.from_messages([
    ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

ANSWER_SYSTEM_PROMPT = """Eres JusticBot, un asistente legal especializado en expedientes judiciales de Costa Rica.

DOCUMENTOS RECUPERADOS:
{context}

FORMATO DE RESPUESTA - MARKDOWN PURO:

Responde SIEMPRE usando Markdown:
- Usa **doble asterisco** para negritas en: expedientes, artículos, términos legales clave
- Usa guiones (-) para crear listas con viñetas
- Deja línea en blanco entre párrafos
- NO uses HTML (<b>, <strong>, <br>, <p>)

EJEMPLO CORRECTO:
**Sí**, encontré aplicación del **artículo 169** en el expediente **22-000191-0386-CI**:

- **Documento**: Resolución PDF5
- **Contexto**: Medida cautelar en proceso arbitral
- **Referencia**: El tribunal menciona el artículo 169 de la LOPJ

Esta referencia constituye una aplicación concreta del artículo en el procedimiento.

INSTRUCCIONES:
- Responde solo con información de los documentos recuperados arriba
- Usa lenguaje profesional pero claro
- Si no encuentras información relevante, di: "No encontré información sobre esto en la base de datos"
- Siempre cita el expediente y documento específico de donde sacas la información

RESPONDE AHORA:"""

# Prompt template simple (el formateo se hace en FormattedRetriever)
DOCUMENT_PROMPT = PromptTemplate.from_template("{page_content}")

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
    
    # Envolver el retriever con FormattedRetriever para agregar metadata visible
    formatted_retriever = FormattedRetriever(retriever)
    
    history_aware_retriever = create_history_aware_retriever(
        llm=llm,
        retriever=formatted_retriever,
        prompt=CONTEXTUALIZE_Q_PROMPT,
    )
    
    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=ANSWER_PROMPT,
        document_prompt=DOCUMENT_PROMPT
    )
    
    rag_chain = create_retrieval_chain(
        history_aware_retriever,
        question_answer_chain,
    )
    
    # Debug: interceptar el chain para ver el contexto enviado
    async def debug_context_wrapper(input_dict):
        """Wrapper para logging del contexto antes de enviarlo al LLM."""
        if "context" in input_dict:
            context = input_dict["context"]
            if isinstance(context, list):
                total_chars = sum(len(doc.page_content) for doc in context)
                logger.info(f"Contexto enviado al LLM: {len(context)} docs, {total_chars} chars (~{total_chars // 4} tokens)")
                # Log de los primeros 200 chars del primer doc para debugging
                if context:
                    logger.debug(f"Primer doc (preview): {context[0].page_content[:200]}...")
        return input_dict
    
    
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
                    
                    # Emitir solo si hay contenido (permitir espacios y saltos de línea)
                    if content_str:
                        total_chars += len(content_str)
                        chunk_data = {
                            "type": "chunk",
                            "content": content_str,
                            "done": False
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
        
        logger.info(f"Streaming completado: {total_chars} caracteres generados")
        
        # Detectar respuestas vacías y enviar fallback ANTES del done
        if total_chars == 0:
            logger.warning("No se generó contenido, enviando mensaje de fallback")
            fallback_message = "No encontré información relevante en los documentos recuperados para responder tu pregunta."
            fallback_data = {
                "type": "chunk",
                "content": fallback_message,
                "done": False
            }
            yield f"data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n"
        
        # Señal de finalización SIEMPRE al final
        done_data = {"type": "done", "content": "", "done": True}
        yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
        
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