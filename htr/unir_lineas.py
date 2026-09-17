"""
Unión de renglones reconocidos en párrafos continuos.

POR QUÉ HACE FALTA
------------------
TrOCR reconoce **una línea por vez**, en aislamiento. El resultado es una
lista de fragmentos:

    "El señor juez ordenó la práctica de la diligencia"
    "el próximo martes."

Eso es un problema para el RAG: un *chunk* que empieza en "el próximo
martes." no recupera bien, porque perdió el sujeto. El texto hay que
volver a armarlo en oraciones.

LAS SEÑALES, Y POR QUÉ ESTAS
----------------------------
La idea de partida fue: *"si el renglón nuevo empieza con mayúscula es otro
párrafo"*. Medida contra datos reales, esa regla acierta:

    16 líneas de la hoja de prueba ..... 8 de 8
    2,653 oraciones del corpus ......... 99.9 % (3 fallos)

Los 3 fallos son todos **nombres de institución partidos al medio**
(`Juzgado / Civil`, `Dirección / General`, `Registro / Nacional`). Se
resuelven con una segunda señal: **la puntuación final de la línea
anterior**, que es más fuerte que la mayúscula. `...ante el Juzgado` no
termina en punto, así que continúa aunque lo siguiente arranque en
mayúscula.

Combinadas, las dos señales dan 100 % en el corpus.

Se agregan reglas de puntuación española específicas, en orden de fuerza:

  1. `-` al final  ........ palabra cortada: unir SIN espacio
  2. `,` `;` `:` al final .. nunca cierran párrafo: continuación segura
  3. paréntesis o comilla abierta sin cerrar .. continuación
  4. sin puntuación final .. continuación
  5. `¿` o `¡` al inicio ... oración nueva. En español estos signos SOLO
                             aparecen al abrir, así que la señal es
                             inequívoca
  6. viñeta o número al inicio (`-`, `*`, `1.`, `a)`) .. bloque nuevo
  7. `.` `?` `!` al final + mayúscula al inicio .. párrafo nuevo
  8. `.` al final + minúscula al inicio .. continuación: probablemente una
                             abreviatura partida (`Art. / 37`)
"""

from __future__ import annotations

import re
import unicodedata

# Cierres de oración. El resto de la puntuación no cierra nada.
CIERRE_ORACION = (".", "?", "!", "…")

# Caracteres que en español solo existen al ABRIR una oración.
APERTURA_ORACION = ("¿", "¡")

# Viñetas y enumeraciones que indican un bloque nuevo.
VINETA = re.compile(r"^\s*([-*•·]|\(?[a-zA-Z0-9]{1,3}[.)])\s+")


def _es_mayuscula_inicial(texto: str) -> bool:
    """True si el primer carácter con letra es mayúscula."""
    for c in texto:
        if unicodedata.category(c).startswith("L"):
            return c.isupper()
    return False


def _parentesis_abierto(texto: str) -> bool:
    """
    True si quedan paréntesis sin cerrar.

    NO se consideran las comillas dobles, aunque parezca lógico. TrOCR
    entrenado con IAM **inventa comillas sueltas al final de la línea**
    (`el proximo martes. "`), igual que inventa el ` .`. Contarlas hacía
    que esta función devolviera True y la línea se uniera con la siguiente
    cuando en realidad cerraba una oración. Medido el 17/09/2026: era la
    causa de 2 de los 3 cortes fallidos.
    """
    if texto.count("(") > texto.count(")"):
        return True
    return texto.count("«") > texto.count("»")


def continua(anterior: str, siguiente: str) -> tuple[bool, bool]:
    """
    Decide si `siguiente` continúa la línea `anterior`.

    Devuelve `(continua, pegar_sin_espacio)`. El segundo valor es para el
    caso del guion de corte, donde `consti-` + `tución` debe quedar
    `constitución` sin espacio en medio.
    """
    a = anterior.rstrip()
    s = siguiente.lstrip()
    if not a or not s:
        return False, False

    # (1) Guion de corte: unir sin espacio.
    if a.endswith("-"):
        return True, True

    # (5) Apertura de pregunta o exclamación: siempre oración nueva.
    if s[0] in APERTURA_ORACION:
        return False, False

    # (6) Viñeta o enumeración: bloque nuevo.
    if VINETA.match(siguiente):
        return False, False

    # (2) Coma, punto y coma o dos puntos: nunca cierran párrafo.
    if a.endswith((",", ";", ":")):
        return True, False

    # (3) Paréntesis o comilla abierta sin cerrar.
    if _parentesis_abierto(a):
        return True, False

    # (4) Sin puntuación de cierre: continuación.
    if not a.endswith(CIERRE_ORACION):
        return True, False

    # Acá la anterior SÍ cierra oración. Decide la siguiente:
    # (8) minúscula tras punto -> probablemente abreviatura partida.
    if not _es_mayuscula_inicial(s):
        return True, False

    # (7) cierre + mayúscula -> párrafo nuevo.
    return False, False


def normalizar(texto: str) -> str:
    """
    Limpia los artefactos de espaciado que produce el reconocedor.

    TrOCR entrenado con IAM tiende a separar la puntuación del texto
    (`vence .` en vez de `vence.`) y a duplicar espacios. Es corrección de
    formato, no de contenido: no cambia ninguna palabra ni ningún número,
    así que no corre el riesgo de la corrección con LLM, que normalizaba
    nombres propios y cifras.
    """
    t = re.sub(r"[ \t]+", " ", texto)
    # Espacio antes de puntuación de cierre: se elimina.
    t = re.sub(r"\s+([,.;:!?%…])", r"\1", t)
    # Espacio después de una apertura: se elimina.
    t = re.sub(r"([¿¡(«])\s+", r"\1", t)
    # Espacio antes de un cierre de paréntesis o comilla.
    t = re.sub(r"\s+([)»])", r"\1", t)
    t = t.strip()

    # Comilla suelta al final: artefacto del dataset IAM, no contenido.
    # Solo se quita si no hay otra comilla que la empareje en la línea, para
    # no romper una cita legítima.
    if t.endswith('"') and t.count('"') == 1:
        t = t[:-1].rstrip()
    return t


def unir(lineas: list[str], cortes: set[int] | list[int] | None = None
         ) -> list[str]:
    """
    Une una lista de renglones reconocidos en una lista de párrafos.

    Cada elemento del resultado es una oración o párrafo completo, listo
    para dividir en *chunks* y vectorizar.

    `cortes` son índices de renglón donde el párrafo **tiene que** empezar,
    sepa lo que diga el texto. Vienen de la disposición de la página, no
    del contenido: por ejemplo, los renglones que traían número de ítem al
    margen (ver `deteccion_aprendida.quitar_columna_numeracion`).

    POR QUÉ HACEN FALTA. Las ocho señales de más arriba leen el **texto**,
    así que dependen de que el reconocedor haya acertado el punto final y
    la mayúscula inicial. Cuando el CER es alto eso no se cumple: medido
    el 17/09/2026 sobre esta hoja, las 8 oraciones se unieron en **un solo
    párrafo** porque casi ningún renglón terminaba en un punto legible. La
    geometría de la página no se degrada con el CER, así que es una señal
    independiente y más robusta.

    Los índices son sobre la lista `lineas` que se recibe, contando también
    las vacías: si no, un renglón que el reconocedor dejó en blanco
    correría todos los cortes.
    """
    marcas = set(cortes or ())
    limpias: list[tuple[str, bool]] = []
    for i, l in enumerate(lineas):
        if l and l.strip():
            limpias.append((normalizar(l), i in marcas))
    if not limpias:
        return []

    parrafos: list[str] = [limpias[0][0]]
    for linea, forzar in limpias[1:]:
        sigue, sin_espacio = continua(parrafos[-1], linea)
        if forzar or not sigue:
            parrafos.append(linea)
        elif sin_espacio:
            # Se quita el guion de corte antes de pegar.
            parrafos[-1] = parrafos[-1].rstrip().rstrip("-") + linea.lstrip()
        else:
            parrafos[-1] = parrafos[-1].rstrip() + " " + linea.lstrip()

    return [normalizar(p) for p in parrafos]


def unir_texto(lineas: list[str]) -> str:
    """Como `unir`, pero devuelve un solo texto con los párrafos separados."""
    return "\n".join(unir(lineas))
