"""Métricas puras para evaluar el reconocimiento de texto impreso (spec 001).

Sin GPU, red ni modelos: solo texto. Así las pruebas pueden importarlas sin
cargar torch ni docTR (plan, decisión 9).

Definiciones de la spec 001:

* CER de página: distancia de edición por carácter entre el texto reconocido
  de la página completa y su referencia, dividida entre la longitud de la
  referencia. Antes de comparar, ambos textos se normalizan a Unicode NFC y
  los espacios y saltos seguidos se reducen a un solo espacio. No se
  normalizan mayúsculas, tildes ni puntuación.
* CER promedio: la media de los CER de página (no ponderada por longitud).
* Acierto en caracteres del español: para cada á é í ó ú ñ ü ¿ ¡ de la
  referencia, si el texto reconocido tiene el mismo carácter en la posición
  alineada por distancia de edición.
* Elección del ganador (N-6) y sus marcas: proponer RF-09 «Parcial» (N-7) y
  cambio de requisito (N-8).

La distancia y la alineación vienen de rapidfuzz, que ya está instalado como
dependencia de docTR.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field

from rapidfuzz.distance import Levenshtein

CARACTERES_ESPANOL = "áéíóúñü¿¡"

_ESPACIOS = re.compile(r"\s+")


def normalizar(texto: str) -> str:
    """Unicode NFC y cada racha de espacios o saltos de línea como un espacio.

    También quita los espacios de los extremos, para que un salto de línea
    final del archivo de referencia no cuente como carácter.
    """
    return _ESPACIOS.sub(" ", unicodedata.normalize("NFC", texto)).strip()


def cer_pagina(referencia: str, reconocido: str) -> float:
    """CER de una página. Un texto reconocido vacío da 1."""
    ref = normalizar(referencia)
    if not ref:
        raise ValueError("El texto de referencia está vacío: no se puede calcular el CER.")
    return Levenshtein.distance(ref, normalizar(reconocido)) / len(ref)


def cer_promedio(cers: Sequence[float]) -> float:
    """Media de los CER de página: cada página pesa lo mismo."""
    if not cers:
        raise ValueError("No hay ninguna página para calcular el CER promedio.")
    return sum(cers) / len(cers)


def _resumen(aciertos: int, apariciones: int) -> dict:
    return {
        "aciertos": aciertos,
        "apariciones": apariciones,
        "proporcion": aciertos / apariciones if apariciones else None,
    }


def acierto_espanol(referencia: str, reconocido: str) -> dict:
    """Acierto en á é í ó ú ñ ü ¿ ¡, por carácter y en total.

    Devuelve {"por_caracter": {c: resumen}, "total": resumen}, donde cada
    resumen tiene "aciertos", "apariciones" y "proporcion" (None si el
    carácter no aparece en la referencia).
    """
    ref = normalizar(referencia)
    rec = normalizar(reconocido)

    aciertos = dict.fromkeys(CARACTERES_ESPANOL, 0)
    apariciones = dict.fromkeys(CARACTERES_ESPANOL, 0)

    for op in Levenshtein.opcodes(ref, rec):
        for i in range(op.src_start, op.src_end):
            caracter = ref[i]
            if caracter not in apariciones:
                continue
            apariciones[caracter] += 1
            if op.tag == "equal":
                aciertos[caracter] += 1
            elif op.tag == "replace":
                # En Levenshtein cada sustitución es 1 a 1: la posición
                # alineada es el mismo desplazamiento dentro del bloque.
                j = op.dest_start + (i - op.src_start)
                if j < op.dest_end and rec[j] == caracter:
                    aciertos[caracter] += 1
            # "delete": el carácter no está en el texto reconocido.

    return {
        "por_caracter": {
            c: _resumen(aciertos[c], apariciones[c]) for c in CARACTERES_ESPANOL
        },
        "total": _resumen(sum(aciertos.values()), sum(apariciones.values())),
    }


def sumar_aciertos(resultados: Sequence[dict]) -> dict:
    """Suma los aciertos de varias páginas (cada uno de acierto_espanol)."""
    aciertos = dict.fromkeys(CARACTERES_ESPANOL, 0)
    apariciones = dict.fromkeys(CARACTERES_ESPANOL, 0)
    for resultado in resultados:
        for caracter, resumen in resultado["por_caracter"].items():
            aciertos[caracter] += resumen["aciertos"]
            apariciones[caracter] += resumen["apariciones"]
    return {
        "por_caracter": {
            c: _resumen(aciertos[c], apariciones[c]) for c in CARACTERES_ESPANOL
        },
        "total": _resumen(sum(aciertos.values()), sum(apariciones.values())),
    }


# ---------------------------------------------------------------------------
# Elección del ganador y sus marcas (spec 001, N-6, N-7 y N-8)
# ---------------------------------------------------------------------------

LIMITE_VRAM_GB = 2.5
LIMITE_TIEMPO_S = 10.0
LIMITE_CER = 0.10
MARGEN_EMPATE_CER = 0.005
# Tolerancia para comparar decimales: 0,105 - 0,100 no da 0,005 exacto.
_TOLERANCIA = 1e-9

# Números de candidato de la tabla de la spec.
CANDIDATO_LINEA_BASE = 1
CANDIDATOS_CAMBIO_DE_REQUISITO = frozenset({4, 5})  # docTR completo y Tesseract


@dataclass(frozen=True)
class Medicion:
    """Resultado de medir un candidato. Si falló, solo trae el motivo."""

    numero: int
    nombre: str
    cer_promedio: float | None
    vram_pico_gb: float | None
    tiempo_promedio_s: float | None
    motivo_sin_medir: str | None = None

    @property
    def medido(self) -> bool:
        return self.motivo_sin_medir is None and self.cer_promedio is not None


@dataclass
class Eleccion:
    ganador: Medicion | None
    listo_para_integrar: bool
    # Por número de candidato: cuánto supera cada límite («cer», «vram_gb»,
    # «tiempo_s»). Solo aparecen los límites superados.
    brechas: dict[int, dict[str, float]] = field(default_factory=dict)
    # Por número de candidato: por qué no entró en la elección.
    excluidos: dict[int, str] = field(default_factory=dict)
    proponer_rf09_parcial: bool = False  # N-7
    cambio_de_requisito: bool = False  # N-8


def _brecha(medicion: Medicion) -> dict[str, float]:
    excesos = {
        "cer": medicion.cer_promedio - LIMITE_CER,
        "vram_gb": medicion.vram_pico_gb - LIMITE_VRAM_GB,
        "tiempo_s": medicion.tiempo_promedio_s - LIMITE_TIEMPO_S,
    }
    return {clave: valor for clave, valor in excesos.items() if valor > _TOLERANCIA}


def _motivo_exclusion(medicion: Medicion) -> str | None:
    if not medicion.medido:
        return f"sin medir: {medicion.motivo_sin_medir or 'sin resultado'}"
    motivos = []
    if medicion.vram_pico_gb > LIMITE_VRAM_GB + _TOLERANCIA:
        motivos.append(
            f"VRAM pico de {medicion.vram_pico_gb:.2f} GB (límite {LIMITE_VRAM_GB} GB)"
        )
    if medicion.tiempo_promedio_s > LIMITE_TIEMPO_S + _TOLERANCIA:
        motivos.append(
            f"tiempo promedio de {medicion.tiempo_promedio_s:.2f} s por página "
            f"(límite {LIMITE_TIEMPO_S:g} s)"
        )
    return "; ".join(motivos) or None


def cumple_criterio(medicion: Medicion) -> bool:
    """Medido, dentro de VRAM y tiempo, y con CER promedio ≤ 0,10."""
    return _motivo_exclusion(medicion) is None and not _brecha(medicion)


def elegir(mediciones: Sequence[Medicion]) -> Eleccion:
    """Elige el ganador según N-6 y calcula las marcas de N-7 y N-8."""
    excluidos: dict[int, str] = {}
    elegibles: list[Medicion] = []
    for medicion in mediciones:
        motivo = _motivo_exclusion(medicion)
        if motivo:
            excluidos[medicion.numero] = motivo
        else:
            elegibles.append(medicion)

    brechas = {
        medicion.numero: brecha
        for medicion in mediciones
        if medicion.medido and (brecha := _brecha(medicion))
    }

    ganador = None
    if elegibles:
        ordenados = sorted(elegibles, key=lambda e: e.cer_promedio)
        ganador = ordenados[0]
        # N-6.2: si el primero y el segundo difieren en 0,005 o menos,
        # gana el de menor VRAM y, si siguen empatados, el de menor tiempo.
        if len(ordenados) > 1:
            segundo = ordenados[1]
            diferencia = segundo.cer_promedio - ganador.cer_promedio
            if diferencia <= MARGEN_EMPATE_CER + _TOLERANCIA:
                ganador = min(
                    (ganador, segundo),
                    key=lambda e: (e.vram_pico_gb, e.tiempo_promedio_s),
                )

    linea_base = next(
        (e for e in mediciones if e.numero == CANDIDATO_LINEA_BASE), None
    )

    return Eleccion(
        ganador=ganador,
        listo_para_integrar=ganador is not None
        and ganador.cer_promedio <= LIMITE_CER + _TOLERANCIA,
        brechas=brechas,
        excluidos=excluidos,
        proponer_rf09_parcial=linea_base is None or not cumple_criterio(linea_base),
        cambio_de_requisito=ganador is not None
        and ganador.numero in CANDIDATOS_CAMBIO_DE_REQUISITO,
    )
