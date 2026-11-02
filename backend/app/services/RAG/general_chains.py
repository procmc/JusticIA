"""
Armado y transmisión de la respuesta del chat (los tres chats: general, por tema y notebook).

Desde la spec 007 no se usan las cadenas de LangChain (`create_stuff_documents_chain`, `RunnableWithMessageHistory`):
cada llamada al motor se arma explícitamente con `presupuesto_contexto`, para que la entrada nunca supere el
presupuesto, cada fragmento aparezca una sola vez y las instrucciones y la pregunta vayan siempre completas.

Flujo de un turno (`CadenaArmada.astream`):
    1. Lee el historial de la sesión.
    2. Chat general con historial: reformula la pregunta con los 2 últimos mensajes (RF-11.66) para buscar.
    3. Recupera los fragmentos y los pasa a `Fragmento` (encabezado con archivo, tema y ruta; RF-12.60).
    4. `armar_respuesta` reparte el presupuesto entre historial y fragmentos y arma
       `[Sistema(instrucciones + lista? + fragmentos), *historial, Humano(pregunta)]`.
    5. Transmite la respuesta del motor y, al terminar, guarda la pregunta y la respuesta en el historial.

`stream_chain_response` convierte ese flujo en eventos SSE (`chunk`, `done`, `error`) y detecta la desconexión.

Ver también:
    * app.services.RAG.presupuesto_contexto: presupuesto y armado
    * app.services.RAG.prompts: textos de instrucciones
    * app.llm.llm_service: servicio del motor
"""
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
import logging
import json

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.llm.llm_service import get_llm
from . import presupuesto_contexto as pc
from .document_formatter import a_fragmento
from .prompts import INSTRUCCION_REFORMULACION, INSTRUCCIONES_GENERAL
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)


class CadenaArmada:
    """Un turno de chat: reformula (solo el general), recupera, arma la entrada dentro del presupuesto y transmite.

    Tiene `astream` como las cadenas de LangChain, así que `stream_chain_response` la consume igual.
    """

    def __init__(
        self,
        chat: str,
        instrucciones: str,
        retriever,
        historial_de: Optional[Callable] = None,
        reformula: bool = False,
    ):
        self.chat = chat
        self.instrucciones = instrucciones
        self.retriever = retriever
        self.historial_de = historial_de  # None: sin historial (ni lectura ni guardado)
        self.reformula = reformula

    async def _reformular(self, llm, pregunta: str, previos: List[BaseMessage]) -> str:
        """RF-11.66: la pregunta autónoma para buscar, con los 2 últimos mensajes que caben; sin ninguno no hay llamada."""
        textos = [str(m.content) for m in previos]
        elegidos = pc.mensajes_para_reformular(INSTRUCCION_REFORMULACION, pregunta, textos)
        if not elegidos:
            return pregunta
        mensajes = [SystemMessage(content=INSTRUCCION_REFORMULACION), *previos[len(previos) - len(elegidos):],
                    HumanMessage(content=pregunta)]
        resultado = await llm.ainvoke(mensajes)
        reformulada = str(getattr(resultado, "content", "") or "").strip()
        logger.info("Pregunta reformulada para buscar (%s -> %s caracteres)", len(pregunta), len(reformulada))
        return reformulada or pregunta

    async def astream(self, input_dict: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> AsyncIterator[dict]:
        pregunta = input_dict["input"]
        historia = None
        previos: List[BaseMessage] = []
        if self.historial_de is not None:
            session_id = ((config or {}).get("configurable") or {}).get("session_id")
            historia = self.historial_de(session_id)
            previos = list(historia.messages)

        llm = await get_llm()
        consulta = await self._reformular(llm, pregunta, previos) if (self.reformula and previos) else pregunta

        documentos = await self.retriever.ainvoke(consulta)
        fragmentos = [a_fragmento(d) for d in documentos]
        entrada = pc.armar_respuesta(
            self.chat, self.instrucciones, pregunta, [str(m.content) for m in previos], fragmentos
        )
        enviados = previos[len(previos) - len(entrada.historial):] if entrada.historial else []
        mensajes = [SystemMessage(content=entrada.sistema), *enviados, HumanMessage(content=pregunta)]
        logger.info(
            "Entrada armada (%s): %s fragmentos de %s recuperados, %s mensajes de historial, ~%s tokens",
            self.chat, len(entrada.fragmentos), len(fragmentos), len(enviados), entrada.tokens_total,
        )

        texto = []
        async for trozo in llm.astream(mensajes):
            contenido = getattr(trozo, "content", trozo)
            if contenido:
                texto.append(contenido if isinstance(contenido, str) else str(contenido))
                yield {"answer": texto[-1]}

        if historia is not None:
            historia.add_messages([HumanMessage(content=pregunta), AIMessage(content="".join(texto))])


async def create_conversational_rag_chain(
    retriever,
    with_history: bool = True,
    session_config_key: str = "configurable"
) -> CadenaArmada:
    """Chat general (RF-11.65/66): reformula con el historial, recupera y responde con las instrucciones generales."""
    return CadenaArmada(
        pc.CHAT_GENERAL, INSTRUCCIONES_GENERAL, retriever,
        historial_de=get_session_history_func() if with_history else None, reformula=True,
    )


async def stream_chain_response(chain, input_dict: Dict[str, Any], config: Dict[str, Any], http_request=None):
    total_chars = 0
    client_disconnected = False
    
    try:
        # Stream desde la chain
        async for chunk in chain.astream(input_dict, config=config):
            # Verificar si el cliente se desconectó ANTES de procesar el chunk
            if http_request:
                try:
                    # Verificar si el cliente sigue conectado
                    if await http_request.is_disconnected():
                        logger.warning("Cliente desconectado detectado - Deteniendo generación de respuesta")
                        client_disconnected = True
                        break
                except Exception as e:
                    # Si hay algún error verificando la conexión, continuar
                    logger.debug(f"No se pudo verificar estado de conexión: {e}")
            
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
                        try:
                            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        except Exception as yield_error:
                            # Si falla el yield, probablemente el cliente se desconectó
                            logger.warning(f"Error al enviar chunk (cliente desconectado): {yield_error}")
                            client_disconnected = True
                            break
        
        # Log final dependiendo de si se completó o se detuvo
        if client_disconnected:
            logger.info(f"Streaming detenido por desconexión del cliente - {total_chars} caracteres generados antes de detener")
        else:
            logger.info(f"Streaming completado: {total_chars} caracteres generados")
        
        # Solo enviar mensajes finales si el cliente NO se desconectó
        if not client_disconnected:
            # Detectar respuestas vacías y enviar fallback ANTES del done
            if total_chars == 0:
                logger.warning("No se generó contenido, enviando mensaje de fallback")
                fallback_message = "No encontré información relevante en los documentos recuperados para responder tu pregunta."
                fallback_data = {
                    "type": "chunk",
                    "content": fallback_message,
                    "done": False
                }
                try:
                    yield f"data: {json.dumps(fallback_data, ensure_ascii=False)}\n\n"
                except:
                    pass  # Cliente ya desconectado
            
            # Señal de finalización SIEMPRE al final
            done_data = {"type": "done", "content": "", "done": True}
            try:
                yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
            except:
                pass  # Cliente ya desconectado
        
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