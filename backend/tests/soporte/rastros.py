"""Búsqueda de un secreto en los rastros de un flujo (spec 003a, RNF-08.1 y RNF-08.2).

Una contraseña temporal, un código de verificación o el correo completo de una persona no deben quedar en lo que un
flujo deja a la vista: la salida estándar y de error, los registros del servidor, las filas de la bitácora y los cuerpos
de las respuestas. Este auxiliar busca el valor en esas fuentes y, si lo encuentra, falla diciendo DÓNDE pero nunca
mostrándolo (ni en el mensaje ni en la traza), para que el propio informe de la prueba no filtre el secreto.

- `encontrar_en_rastros(valor, **fuentes)`: devuelve los nombres de las fuentes donde está el valor (vacía si no está).
  Sirve también de control positivo: la prueba comprueba que el valor SÍ está donde debe estar (por ejemplo, en el correo
  simulado) para saber que la búsqueda no es en vacío.
- `buscar_en_rastros(valor, **fuentes)`: falla si el valor aparece en alguna fuente.
- `valor_tras(texto, marcador)`: saca de un correo el valor que sigue a un marcador (la contraseña temporal) envuelto
  en `Contrasena`, cuyo `repr` no lo muestra.

Cada fuente es un texto, `bytes`, un diccionario o lista (se busca en su JSON) o un conjunto de esos (por ejemplo, las
filas de la bitácora). Una fuente `None` o vacía cuenta como vacía: un flujo puede no escribir nada. Un valor vacío o
la ausencia total de fuentes son errores de la prueba (`ValueError`), porque no probarían nada.

Este módulo no importa `app` ni nada que se conecte al cargarse.
"""
import json
import re
from typing import Any, List

import pytest

from tests.soporte.datos import Contrasena


def _textos(fuente: Any) -> List[str]:
    """Aplana una fuente a una lista de textos donde buscar."""
    if fuente is None:
        return []
    if isinstance(fuente, str):
        return [fuente]
    if isinstance(fuente, (bytes, bytearray)):
        return [bytes(fuente).decode("utf-8", errors="replace")]
    if isinstance(fuente, dict):
        return [json.dumps(fuente, ensure_ascii=False, default=str)]
    if isinstance(fuente, (list, tuple, set, frozenset)):
        return [texto for elemento in fuente for texto in _textos(elemento)]
    return [str(fuente)]


def encontrar_en_rastros(valor: Any, **fuentes: Any) -> List[str]:
    """Los nombres de las fuentes (en el orden en que se dieron) cuyo contenido incluye `valor`.

    `ValueError` si el valor está vacío o no se da ninguna fuente: esa búsqueda no probaría nada.
    """
    if valor is None or str(valor) == "":
        raise ValueError("La búsqueda en los rastros necesita un valor no vacío: un texto vacío «está» en cualquier fuente.")
    if not fuentes:
        raise ValueError("La búsqueda en los rastros necesita al menos una fuente (salida, registros, bitacora, respuestas...).")
    buscado = str(valor)
    return [nombre for nombre, fuente in fuentes.items() if any(buscado in texto for texto in _textos(fuente))]


def buscar_en_rastros(valor: Any, **fuentes: Any) -> None:
    """Falla si `valor` aparece en alguna fuente. El mensaje nombra las fuentes y NO repite el valor."""
    encontradas = encontrar_en_rastros(valor, **fuentes)
    if encontradas:
        pytest.fail(
            "Un valor que no debía quedar a la vista apareció en: " + ", ".join(encontradas)
            + " (el valor no se muestra).",
            pytrace=False,
        )


def valor_tras(texto: str, marcador: str, patron: str = r"[A-Za-z0-9]+") -> Contrasena:
    """El primer valor que coincide con `patron` justo después de `marcador` (se admiten espacios entre ambos).

    Por omisión toma letras y números, así que en un cuerpo HTML termina donde empieza la siguiente etiqueta. Si el
    marcador no está, lanza `LookupError` sin repetir el contenido del correo. El resultado es una `Contrasena`: sigue
    siendo un texto, pero su `repr` no lo muestra.
    """
    coincidencia = re.search(re.escape(marcador) + r"\s*(" + patron + ")", texto or "")
    if coincidencia is None:
        raise LookupError("No se encontró el marcador en el contenido (o no le sigue un valor con la forma esperada).")
    return Contrasena(coincidencia.group(1))
