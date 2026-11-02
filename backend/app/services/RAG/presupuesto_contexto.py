"""Presupuesto y armado de la entrada del chat (spec 007: RF-11.61, RF-11.62, RF-11.65, RF-12.60, RF-12.62).

Módulo puro: no llama al motor, a Qdrant ni a la base de datos. Calcula cuántos tokens caben en una llamada
al motor, decide si la pregunta cabe (RF-11.62) y reparte el espacio entre historial y fragmentos
(RF-11.61), siempre con los valores de `app.config.contexto_config.CONFIGURACION`, para que el cálculo y la
llamada al motor coincidan. Las instrucciones y la pregunta nunca se recortan.

Ver también: `app.config.contexto_config` (valores), `app.services.RAG.rag_chain_service` (quien lo usará).
"""
import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from app.config.contexto_config import (
    CARACTERES_ENCABEZADO,
    CARACTERES_LINEA_NOTEBOOK,
    CONFIGURACION,
    ConfiguracionContexto,
)

logger = logging.getLogger(__name__)

CHAT_GENERAL = "general"
CHAT_TEMA = "tema"
CHAT_NOTEBOOK = "notebook"
FRACCION_HISTORIAL = 0.2
MENSAJES_DE_REFORMULACION = 2
TITULO_FRAGMENTOS = "FRAGMENTOS RECUPERADOS:\n"
TITULO_LISTA = "ARCHIVOS DE ESTA CONSULTA:\n"  # la regla 3 de las instrucciones del notebook lo cita por este nombre


@dataclass(frozen=True)
class Fragmento:
    texto: str
    archivo: str
    tema: str
    ruta: str
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None
    es_imagen: bool = False


@dataclass
class EntradaArmada:
    """Resultado del armado: lo que se envía al motor y lo que quedó dentro."""
    sistema: str
    historial: List[str]
    pregunta: str
    fragmentos: List[Fragmento] = field(default_factory=list)
    archivos: List[str] = field(default_factory=list)
    tokens_total: int = 0


def tokens(texto: str, cfg: ConfiguracionContexto = CONFIGURACION) -> int:
    """Estimación prudente de tokens: se redondea hacia arriba por pieza."""
    return math.ceil(len(texto) / cfg.caracteres_por_token)


def espacio_minimo(chat: str, cfg: ConfiguracionContexto = CONFIGURACION) -> int:
    """Tokens que se reservan para un fragmento de tamaño máximo con su encabezado (y su línea, en el notebook)."""
    caracteres = cfg.fragmento_tamano_maximo + CARACTERES_ENCABEZADO
    if chat == CHAT_NOTEBOOK:
        caracteres += CARACTERES_LINEA_NOTEBOOK
    return tokens(" " * caracteres, cfg)


def _base_sistema(chat: str, instrucciones: str) -> str:
    """Instrucciones completas más los títulos fijos (cuentan como instrucciones)."""
    titulos = (TITULO_LISTA if chat == CHAT_NOTEBOOK else "") + TITULO_FRAGMENTOS
    return instrucciones + "\n\n" + titulos


def cabe_la_pregunta(chat: str, instrucciones: str, pregunta: str,
                     cfg: ConfiguracionContexto = CONFIGURACION) -> bool:
    """RF-11.62: instrucciones, pregunta y espacio mínimo de fragmento caben en el presupuesto (sin historial)."""
    total = tokens(_base_sistema(chat, instrucciones), cfg) + tokens(pregunta, cfg) + espacio_minimo(chat, cfg)
    return total <= cfg.presupuesto


def cantidad_a_recuperar(solicitud: Optional[int], cfg: ConfiguracionContexto = CONFIGURACION) -> int:
    """RF-11.65: la solicitud puede pedir menos que el servidor, nunca más; ausente o ≤ 0 usa el del servidor."""
    configurada = cfg.fragmentos_por_consulta
    if solicitud is None or solicitud <= 0:
        return configurada
    return min(solicitud, configurada)


def encabezado(n: int, f: Fragmento) -> str:
    """RF-12.60: archivo, tema, páginas y ruta de descarga del fragmento."""
    paginas = ""
    if f.pagina_inicio is not None:
        fin = f.pagina_fin if f.pagina_fin is not None else f.pagina_inicio
        paginas = f" | Págs.: {f.pagina_inicio}-{fin}"
    texto = f"[Fragmento {n}] Archivo: {f.archivo} | Tema: {f.tema}{paginas}\n"
    if f.es_imagen:
        texto += "Origen: documento escaneado, ya transcrito automáticamente a texto\n"
    return texto + f"Ruta: {f.ruta}\n"


def _linea_lista(archivo: str) -> str:
    return f'- "{archivo}"\n'


def armar_respuesta(chat: str, instrucciones: str, pregunta: str, historial: Sequence[str],
                    fragmentos: Sequence[Fragmento], solicitud: Optional[int] = None,
                    cfg: ConfiguracionContexto = CONFIGURACION) -> EntradaArmada:
    """RF-11.61: reparte el presupuesto entre historial (≤ 20 %) y fragmentos (hasta k, enteros).

    `historial` va del más antiguo al más reciente, un texto por mensaje. Se asume que `cabe_la_pregunta`
    ya se verificó; si no, el espacio de fragmentos queda en 0 y se registra el aviso.
    """
    presupuesto = cfg.presupuesto
    base_texto = _base_sistema(chat, instrucciones)
    base = tokens(base_texto, cfg) + tokens(pregunta, cfg)

    tope_historial = max(0, min(FRACCION_HISTORIAL * presupuesto, presupuesto - base - espacio_minimo(chat, cfg)))
    elegido: List[str] = []
    usado = 0
    for mensaje in reversed(historial):
        costo = tokens(mensaje, cfg)
        if usado + costo > tope_historial:
            break  # el que no cabe se omite junto con los anteriores
        elegido.insert(0, mensaje)
        usado += costo

    libre = presupuesto - base - usado
    enviados: List[Fragmento] = []
    archivos: List[str] = []
    bloques: List[str] = []
    lineas: List[str] = []
    for f in list(fragmentos)[:cantidad_a_recuperar(solicitud, cfg)]:
        bloque = encabezado(len(enviados) + 1, f) + f.texto + "\n\n"
        costo = tokens(bloque, cfg)
        linea = ""
        if chat == CHAT_NOTEBOOK and f.archivo not in archivos:
            linea = _linea_lista(f.archivo)
            costo += tokens(linea, cfg)
        if costo <= libre:
            libre -= costo
            enviados.append(f)
            bloques.append(bloque)
            if linea:
                archivos.append(f.archivo)
                lineas.append(linea)

    if chat == CHAT_NOTEBOOK:
        sistema = (instrucciones + "\n\n" + TITULO_LISTA + "".join(lineas) + "\n"
                   + TITULO_FRAGMENTOS + "".join(bloques))
    else:
        sistema = base_texto + "".join(bloques)

    # Suma de piezas redondeadas: nunca menor que el total real del estimador.
    total = base + usado + sum(tokens(b, cfg) for b in bloques) + sum(tokens(li, cfg) for li in lineas)
    if total > presupuesto:
        logger.error("La entrada armada (%s tokens) supera el presupuesto (%s).", total, presupuesto)
    return EntradaArmada(sistema=sistema, historial=elegido, pregunta=pregunta, fragmentos=enviados,
                         archivos=archivos, tokens_total=total)


def mensajes_para_reformular(instrucciones: str, pregunta: str, historial: Sequence[str],
                             cfg: ConfiguracionContexto = CONFIGURACION) -> List[str]:
    """RF-11.66: hasta los 2 últimos mensajes que caben; si no cabe ninguno (o no hay) devuelve [] (sin llamada)."""
    mensajes = list(historial)[-MENSAJES_DE_REFORMULACION:]
    fijo = tokens(instrucciones, cfg) + tokens(pregunta, cfg)
    while mensajes and fijo + sum(tokens(m, cfg) for m in mensajes) > cfg.presupuesto:
        mensajes = mensajes[1:]  # se omite el más antiguo
    return mensajes
