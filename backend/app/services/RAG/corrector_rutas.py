"""Corrector de rutas de la respuesta del chat (RF-12.1, RF-18.20).

Las instrucciones piden al modelo copiar la ruta de cada fuente tal cual (`uploads/<tema>/<archivo>`), pero a veces «corrige» la
ortografía (`deposito` → `depósito`, `Filosofa` → `Filosofía`) y el enlace de descarga deja de coincidir con el archivo. Este módulo
cambia una ruta escrita por la ruta REGISTRADA de la misma carpeta que mejor coincide, solo cuando la coincidencia es clara. No
afloja la descarga: esta sigue exigiendo la ruta exacta de un documento registrado, procesado y propio (RNF-07.20); aquí solo se
evita que el modelo la rompa al escribirla. Las rutas candidatas las da quien lo usa (`conocidas_de`), ya limitadas a lo que el
usuario puede ver.

Módulo sin base de datos ni red: `CorrectorDeRutas` procesa el texto a medida que llega (SSE) y solo retiene lo que podría ser
el inicio de una ruta.

Ver también: `app.services.RAG.general_chains.stream_chain_response` (quien lo aplica) y `rag_chain_service` (quien lo arma).
"""
import difflib
import logging
import re
import unicodedata
from typing import Callable, List, Optional, Sequence

logger = logging.getLogger(__name__)

MARCADOR = "uploads/"
UMBRAL_DE_PARECIDO = 0.90      # por debajo, no se cambia nada
MARGEN_SOBRE_LA_SEGUNDA = 0.03  # la mejor debe ganarle a la siguiente por esta diferencia; si no, es ambiguo y no se adivina
LARGO_MAXIMO_RETENIDO = 400     # una ruta sin cierre no retiene la respuesta más que esto


def _clave(texto: str) -> str:
    """El texto sin tildes, sin mayúsculas y con los espacios normalizados, para comparar rutas."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip().casefold()


def ruta_mas_parecida(escrita: str, conocidas: Sequence[str]) -> Optional[str]:
    """La ruta conocida que el modelo quiso escribir, o None si `escrita` ya es una de ellas o no hay una clara.

    Una coincidencia clara es la única ruta con la misma clave (sin tildes ni mayúsculas) o la que supera el umbral de parecido y
    le gana a la siguiente por el margen. Con dos candidatas casi iguales no se adivina: es peor abrir otro documento que ninguno.
    """
    if not conocidas or escrita in conocidas:
        return None
    clave_escrita = _clave(escrita)
    iguales = [c for c in conocidas if _clave(c) == clave_escrita]
    if len(iguales) == 1:
        return iguales[0]
    if len(iguales) > 1:
        return None
    puntuadas = sorted(
        ((difflib.SequenceMatcher(None, clave_escrita, _clave(c)).ratio(), c) for c in conocidas), reverse=True)
    mejor = puntuadas[0]
    if mejor[0] < UMBRAL_DE_PARECIDO:
        return None
    if len(puntuadas) > 1 and mejor[0] - puntuadas[1][0] < MARGEN_SOBRE_LA_SEGUNDA:
        return None
    return mejor[1]


class CorrectorDeRutas:
    """Corrige las rutas de un texto que llega en trozos. `conocidas_de(carpeta)` da las rutas registradas y visibles de esa carpeta."""

    def __init__(self, conocidas_de: Callable[[str], Sequence[str]]):
        self._conocidas_de = conocidas_de
        self._pendiente = ""

    def procesar(self, texto: str) -> str:
        """Lo que ya se puede entregar tras recibir `texto`. Retiene el inicio de una ruta hasta ver dónde termina (un paréntesis
        de cierre o un salto de línea) y la cola del texto que podría ser el comienzo de «uploads/»."""
        self._pendiente += texto
        salida: List[str] = []
        while True:
            posicion = self._pendiente.find(MARCADOR)
            if posicion == -1:
                retener = next((k for k in range(len(MARCADOR) - 1, 0, -1) if self._pendiente.endswith(MARCADOR[:k])), 0)
                limite = len(self._pendiente) - retener
                salida.append(self._pendiente[:limite])
                self._pendiente = self._pendiente[limite:]
                break
            salida.append(self._pendiente[:posicion])
            self._pendiente = self._pendiente[posicion:]
            fines = [i for i in (self._pendiente.find(")"), self._pendiente.find("\n")) if i != -1]
            if not fines:
                if len(self._pendiente) > LARGO_MAXIMO_RETENIDO:
                    salida.append(self._pendiente)  # no parece una ruta: no se retiene la respuesta
                    self._pendiente = ""
                break
            fin = min(fines)
            salida.append(self._corregir(self._pendiente[:fin]))
            self._pendiente = self._pendiente[fin:]
        return "".join(salida)

    def vaciar(self) -> str:
        """Lo que quedó retenido al terminar la respuesta. Una ruta sin cierre se intenta corregir igual."""
        resto, self._pendiente = self._pendiente, ""
        return self._corregir(resto) if resto.startswith(MARCADOR) else resto

    def _corregir(self, ruta: str) -> str:
        nucleo = ruta.rstrip()
        cola = ruta[len(nucleo):]
        partes = nucleo.split("/")
        if len(partes) < 3 or not partes[1]:
            return ruta
        try:
            mejor = ruta_mas_parecida(nucleo, self._conocidas_de(partes[1]))
        except Exception as error:  # sin poder consultar, el texto pasa tal cual
            logger.warning("No se pudieron consultar las rutas conocidas para corregir una ruta (%s)", type(error).__name__)
            return ruta
        return (mejor or nucleo) + cola
