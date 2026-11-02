"""
Armado y transmisión de la respuesta del chat (los tres chats: general, por tema y notebook).

Desde la spec 007 no se usan las cadenas de LangChain (`create_stuff_documents_chain`, `RunnableWithMessageHistory`):
cada llamada al motor se arma explícitamente con `presupuesto_contexto`, para que la entrada nunca supere el
presupuesto, cada fragmento aparezca una sola vez y las instrucciones y la pregunta vayan siempre completas.

Flujo de un turno (`CadenaArmada.astream`), que emite sus pasos como diccionarios (`etapa` y `answer`):
    1. Etapa «Procesando consulta»: lee el historial de la sesión y, en los tres chats con historial, reformula la pregunta
       con los 2 últimos mensajes (RF-11.66) para buscar.
    2. Etapa «Analizando documentos»: recupera los fragmentos y los pasa a `Fragmento` (RF-12.60).
    3. Etapa «Generando respuesta»: `armar_respuesta` reparte el presupuesto entre historial y fragmentos y arma
       `[Sistema(instrucciones + lista? + fragmentos), *historial, Humano(pregunta)]`; transmite lo que responde el motor.

`stream_chain_response` es el orquestador del turno (RF-11.62, RF-11.64, RF-11.68, RF-16.60, RF-16.62, RF-21.60): corre la cadena
en una tarea aparte para poder medir el tiempo, convierte sus pasos en eventos SSE (`etapa`, `vida`, `chunk`, `done`, `error`),
envía una señal de vida mientras el motor no entrega nada, corta al llegar el tope, detiene la generación si el usuario se
desconecta, y guarda el historial y registra la bitácora solo cuando el turno termina.

Ver también:
    * app.services.RAG.presupuesto_contexto: presupuesto y armado
    * app.services.RAG.prompts: textos de instrucciones
    * app.llm.llm_service: servicio del motor
    * app.utils.reloj: el reloj que mide la señal de vida y el tope (controlable en las pruebas)
"""
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional
import asyncio
import logging
import json

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.config.contexto_config import CONFIGURACION
from app.llm.llm_service import get_llm
from app.utils.reloj import obtener_reloj
from . import presupuesto_contexto as pc
from .document_formatter import a_fragmento
from .prompts import INSTRUCCION_REFORMULACION, INSTRUCCIONES_GENERAL
from .session_store import get_session_history_func

logger = logging.getLogger(__name__)

# Etapas que informa el servidor (RF-11.64)
ETAPA_PROCESANDO = "Procesando consulta"
ETAPA_ANALIZANDO = "Analizando documentos"
ETAPA_GENERANDO = "Generando respuesta"

# Errores que el servidor envía por su cuenta (RF-11.62, RF-16.62) y motivos fijos de la bitácora (RF-21.60)
MSG_LARGA = "La pregunta es demasiado larga. Acórtela e intente de nuevo."
MSG_TOPE = "La consulta tardó demasiado. Intente de nuevo."
MOTIVO_LARGA = "pregunta demasiado larga"
MOTIVO_TOPE = "tiempo máximo agotado"
MOTIVO_ERROR_MOTOR = "error del motor"
MSG_SIN_RESPUESTA = "No encontré información relevante en los documentos recuperados para responder tu pregunta."

# Lo que la tarea productora deja en la cola del turno
_EVENTO, _FIN, _ERROR = "evento", "fin", "error"

# Quien registra el turno en la bitácora: recibe el motivo (`None` si el turno terminó bien)
Registrador = Callable[[Optional[str]], Awaitable[None]]


class CadenaArmada:
    """Un turno de chat: reformula (solo el general), recupera, arma la entrada dentro del presupuesto y transmite.

    Tiene `astream` como las cadenas de LangChain, pero emite `{"etapa": ...}` y `{"answer": ...}`; el historial lo guarda
    `guardar_turno`, que llama el orquestador solo cuando el turno terminó (RF-11.68).
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

    def cabe_la_pregunta(self, pregunta: str) -> bool:
        """RF-11.62: instrucciones, pregunta y espacio mínimo de fragmento caben en el presupuesto."""
        return pc.cabe_la_pregunta(self.chat, self.instrucciones, pregunta)

    def guardar_turno(self, pregunta: str, respuesta: str, config: Optional[Dict[str, Any]] = None) -> None:
        """RF-11.68: deja la pregunta y la respuesta en el historial de la sesión, juntas. Solo la llama el turno terminado."""
        if self.historial_de is None:
            return
        session_id = ((config or {}).get("configurable") or {}).get("session_id")
        self.historial_de(session_id).add_messages([HumanMessage(content=pregunta), AIMessage(content=respuesta)])

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
        previos: List[BaseMessage] = []
        if self.historial_de is not None:
            session_id = ((config or {}).get("configurable") or {}).get("session_id")
            previos = list(self.historial_de(session_id).messages)

        yield {"etapa": ETAPA_PROCESANDO}
        llm = await get_llm()
        consulta = await self._reformular(llm, pregunta, previos) if (self.reformula and previos) else pregunta

        yield {"etapa": ETAPA_ANALIZANDO}
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

        yield {"etapa": ETAPA_GENERANDO}
        async for trozo in llm.astream(mensajes):
            contenido = getattr(trozo, "content", trozo)
            if contenido:
                yield {"answer": contenido if isinstance(contenido, str) else str(contenido)}


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


def _evento(tipo: str, contenido: str = "", terminado: bool = False) -> str:
    """Un evento SSE del turno: `data: {"type", "content", "done"}`."""
    return f"data: {json.dumps({'type': tipo, 'content': contenido, 'done': terminado}, ensure_ascii=False)}\n\n"


async def _desconectado(http_request) -> bool:
    """¿El cliente cerró la conexión? Si no se puede saber, se asume que sigue conectado."""
    if http_request is None:
        return False
    try:
        return bool(await http_request.is_disconnected())
    except Exception as error:
        logger.debug("No se pudo verificar el estado de la conexión: %s", error)
        return False


async def _detener(tarea: "asyncio.Future") -> None:
    """Cancela la tarea del turno y espera a que termine de cancelarse: así la petición al motor se cierra y el motor queda libre."""
    if not tarea.done():
        tarea.cancel()
    await asyncio.wait({tarea})


async def _registrar(registrar: Optional[Registrador], motivo: Optional[str]) -> None:
    """RF-21.60: deja el turno en la bitácora. Si el registro falla, el turno continúa (RF-21)."""
    if registrar is None:
        return
    try:
        await registrar(motivo)
    except Exception as error:
        logger.warning("No se pudo registrar el turno en la bitácora: %s", type(error).__name__)


async def stream_chain_response(
    chain,
    input_dict: Dict[str, Any],
    config: Dict[str, Any],
    http_request=None,
    registrar: Optional[Registrador] = None,
    al_terminar: Optional[Callable[[], None]] = None,
):
    """Orquesta un turno y entrega sus eventos SSE.

    `registrar(motivo)` deja el turno en la bitácora (una vez por turno; ninguna si el usuario se desconecta) y `al_terminar()`
    se llama solo si el turno terminó bien (genera el título de la conversación). Ambos ocurren antes del evento final.
    """
    pregunta = input_dict["input"]

    # RF-11.62: una pregunta que no cabe se rechaza antes de cualquier etapa o llamada al motor
    cabe = getattr(chain, "cabe_la_pregunta", None)
    if cabe is not None and not cabe(pregunta):
        logger.info("Pregunta rechazada: no cabe en el presupuesto de entrada")
        await _registrar(registrar, MOTIVO_LARGA)
        yield _evento("error", MSG_LARGA, True)
        return

    reloj = obtener_reloj()
    senal_de_vida = CONFIGURACION.senal_de_vida_segundos
    cola: "asyncio.Queue" = asyncio.Queue()

    async def producir() -> None:
        try:
            async for evento in chain.astream(input_dict, config=config):
                await cola.put((_EVENTO, evento))
            await cola.put((_FIN, None))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error("Error en streaming: %s", error, exc_info=True)
            await cola.put((_ERROR, error))

    limite = reloj.monotonico() + CONFIGURACION.tiempo_maximo_segundos
    productor = asyncio.ensure_future(producir())
    texto: List[str] = []
    try:
        while True:
            restante = limite - reloj.monotonico()
            if restante <= 0:  # RF-16.62: tope por consulta
                logger.warning("Consulta detenida: superó el tiempo máximo")
                await _detener(productor)
                await _registrar(registrar, MOTIVO_TOPE)
                yield _evento("error", MSG_TOPE, True)
                return

            try:
                clase, valor = await reloj.con_limite(cola.get(), min(senal_de_vida, restante))
            except TimeoutError:
                # Nada llegó en un intervalo: si el usuario cerró la conexión se detiene todo; si no, señal de vida (RF-16.60)
                if await _desconectado(http_request):
                    logger.warning("Cliente desconectado: se detiene la generación de la respuesta")
                    await _detener(productor)
                    return
                if limite - reloj.monotonico() > 0:
                    yield _evento("vida")
                continue

            if clase == _ERROR:
                await _registrar(registrar, MOTIVO_ERROR_MOTOR)
                yield _evento("error", f"Error al procesar la consulta: {valor}", True)
                yield _evento("done", "", True)
                return

            if clase == _FIN:
                completo = "".join(texto)
                logger.info("Streaming completado: %s caracteres generados", len(completo))
                if not completo:
                    logger.warning("No se generó contenido, enviando mensaje de fallback")
                    yield _evento("chunk", MSG_SIN_RESPUESTA)
                try:
                    chain.guardar_turno(pregunta, completo, config)
                except Exception:
                    logger.exception("No se pudo guardar el turno en el historial")
                await _registrar(registrar, None)
                if al_terminar is not None:
                    try:
                        al_terminar()
                    except Exception:
                        logger.exception("No se pudo generar el título de la conversación")
                yield _evento("done", "", True)
                return

            if "etapa" in valor:
                yield _evento("etapa", valor["etapa"])
            elif valor.get("answer"):
                if await _desconectado(http_request):
                    logger.warning("Cliente desconectado: se detiene la generación de la respuesta")
                    await _detener(productor)
                    return
                contenido = valor["answer"] if isinstance(valor["answer"], str) else str(valor["answer"])
                texto.append(contenido)
                yield _evento("chunk", contenido)
    finally:
        # Cierre del cliente (GeneratorExit o cancelación de la respuesta): la tarea del turno no debe seguir generando
        if not productor.done():
            productor.cancel()
