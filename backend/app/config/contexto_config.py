"""Configuración única del contexto del chat (spec 007: RF-08.62, RF-11.63, RF-11.65).

Valida una sola vez los valores del entorno que fijan cuánto cabe en una llamada al motor: ventana,
reserva de respuesta, conteo de caracteres por token, fragmentos por consulta, tamaño y solapamiento de
fragmento, intervalo de la señal de vida y tope de la consulta. Si alguno es incoherente (o no es un
número) escribe un aviso con el motivo y usa TODOS los valores por omisión: una mezcla de valores propios
y por omisión podría seguir siendo incoherente, y los de omisión lo son entre sí.

Quien necesite uno de estos valores (`get_llm`, el presupuesto, la fragmentación, la recuperación) lo lee
de `CONFIGURACION`, para que la llamada al motor y el cálculo del presupuesto nunca difieran.

Ver también: `app.config.config` (lee el entorno), `app.llm.llm_service` y `app.config.rag_config`.
"""
import logging
import math
from dataclasses import dataclass
from typing import Mapping, Optional

from app.config import config

logger = logging.getLogger(__name__)

# Estimaciones fijas de la definición «espacio mínimo de fragmento» (spec 007): encabezado del fragmento
# y línea del archivo en la lista del notebook.
CARACTERES_ENCABEZADO = 500
CARACTERES_LINEA_NOTEBOOK = 300
# Parte del presupuesto que el espacio mínimo de fragmento del notebook puede ocupar como máximo.
FRACCION_MAXIMA_ESPACIO_MINIMO = 0.6


@dataclass(frozen=True)
class ConfiguracionContexto:
    ventana: int
    reserva: int
    caracteres_por_token: float
    fragmentos_por_consulta: int
    fragmento_tamano_maximo: int
    fragmento_solapamiento: int
    senal_de_vida_segundos: float
    tiempo_maximo_segundos: float

    @property
    def presupuesto(self) -> int:
        """Entrada máxima por llamada: la ventana menos la reserva de respuesta."""
        return self.ventana - self.reserva


VALORES_POR_OMISION = ConfiguracionContexto(
    ventana=8192,
    reserva=1024,
    caracteres_por_token=2.9,
    fragmentos_por_consulta=8,
    fragmento_tamano_maximo=1500,
    fragmento_solapamiento=200,
    senal_de_vida_segundos=10,
    tiempo_maximo_segundos=180,
)

# Variable de entorno -> (campo, tipo)
_VARIABLES = {
    "LLM_NUM_CTX": ("ventana", int),
    "LLM_NUM_PREDICT": ("reserva", int),
    "CHAT_CARACTERES_POR_TOKEN": ("caracteres_por_token", float),
    "CHAT_FRAGMENTOS_POR_CONSULTA": ("fragmentos_por_consulta", int),
    "FRAGMENTO_TAMANO_MAXIMO": ("fragmento_tamano_maximo", int),
    "FRAGMENTO_SOLAPAMIENTO": ("fragmento_solapamiento", int),
    "CHAT_SENAL_DE_VIDA_SEGUNDOS": ("senal_de_vida_segundos", float),
    "CHAT_TIEMPO_MAXIMO_SEGUNDOS": ("tiempo_maximo_segundos", float),
}


def _motivo_de_incoherencia(c: ConfiguracionContexto) -> Optional[str]:
    """Devuelve el primer motivo por el que `c` es incoherente, o None si lo es."""
    valores = (c.ventana, c.reserva, c.caracteres_por_token, c.fragmentos_por_consulta,
               c.fragmento_tamano_maximo, c.fragmento_solapamiento,
               c.senal_de_vida_segundos, c.tiempo_maximo_segundos)
    if not all(math.isfinite(v) for v in valores):
        return "hay un valor no finito"
    if c.fragmento_tamano_maximo <= 0:
        return "el tamaño máximo de fragmento debe ser mayor que 0"
    if c.fragmento_solapamiento < 0 or c.fragmento_solapamiento >= c.fragmento_tamano_maximo:
        return "el solapamiento debe ser 0 o más y menor que el tamaño de fragmento"
    if c.fragmentos_por_consulta <= 0:
        return "la cantidad de fragmentos por consulta debe ser mayor que 0"
    if c.caracteres_por_token <= 0:
        return "los caracteres por token deben ser mayores que 0"
    if c.ventana <= 0:
        return "la ventana debe ser mayor que 0"
    if c.reserva <= 0:
        return "la reserva de respuesta debe ser mayor que 0"
    if c.reserva >= c.ventana:
        return "la reserva debe ser menor que la ventana (presupuesto <= 0)"
    if c.senal_de_vida_segundos <= 0:
        return "el intervalo de la señal de vida debe ser mayor que 0"
    if c.tiempo_maximo_segundos <= 0:
        return "el tope de la consulta debe ser mayor que 0"
    if c.senal_de_vida_segundos >= c.tiempo_maximo_segundos:
        return "el intervalo de la señal de vida debe ser menor que el tope de la consulta"
    espacio_minimo = math.ceil(
        (c.fragmento_tamano_maximo + CARACTERES_ENCABEZADO + CARACTERES_LINEA_NOTEBOOK) / c.caracteres_por_token
    )
    if espacio_minimo > FRACCION_MAXIMA_ESPACIO_MINIMO * c.presupuesto:
        return (f"el espacio mínimo de fragmento ({espacio_minimo} tokens) supera el 60 % del "
                f"presupuesto ({c.presupuesto} tokens)")
    return None


def construir_configuracion(entorno: Mapping[str, object]) -> ConfiguracionContexto:
    """Arma la configuración desde `entorno`; si es incoherente avisa y devuelve los valores por omisión."""
    valores = {}
    for variable, (campo, tipo) in _VARIABLES.items():
        crudo = entorno.get(variable)
        if crudo is None or str(crudo).strip() == "":
            valores[campo] = getattr(VALORES_POR_OMISION, campo)
            continue
        try:
            valores[campo] = tipo(str(crudo).strip())
        except ValueError:
            logger.warning(
                "Configuración del contexto incoherente: %s no es numérico; se usan todos los valores por omisión.",
                variable,
            )
            return VALORES_POR_OMISION
    candidata = ConfiguracionContexto(**valores)
    motivo = _motivo_de_incoherencia(candidata)
    if motivo:
        logger.warning(
            "Configuración del contexto incoherente: %s; se usan todos los valores por omisión.", motivo
        )
        return VALORES_POR_OMISION
    return candidata


CONFIGURACION = construir_configuracion(config.ENTORNO_CONTEXTO)
