"""Pruebas de las métricas puras de texto impreso (spec 001, N-5 a N-8).

Los valores esperados están calculados a mano en cada caso.
"""

from __future__ import annotations

import pytest

from metricas_impreso import (
    CARACTERES_ESPANOL,
    Medicion,
    acierto_espanol,
    cer_pagina,
    cer_promedio,
    elegir,
    normalizar,
)

# --- Normalización ----------------------------------------------------------


def test_normalizar_nfc_vocal_descompuesta_igual_a_compuesta():
    """N-5: «á» como a + tilde combinable (U+0301) equivale a «á» (U+00E1)."""
    descompuesta = "canción"
    compuesta = "canción"

    assert descompuesta != compuesta
    assert normalizar(descompuesta) == compuesta
    assert cer_pagina(compuesta, descompuesta) == 0.0


def test_normalizar_reduce_espacios_y_saltos_seguidos_a_uno():
    """N-5: espacios, tabulaciones y saltos seguidos quedan como un solo espacio."""
    assert normalizar("hola   mundo\n\n\tadiós") == "hola mundo adiós"
    assert normalizar("uno\r\ndos \n tres") == "uno dos tres"


def test_normalizar_no_toca_mayusculas_tildes_ni_puntuacion():
    """N-5: no se normalizan mayúsculas, tildes ni puntuación."""
    assert normalizar("¿Qué TAL, Señor?") == "¿Qué TAL, Señor?"


def test_cer_no_cuenta_diferencias_de_espacios():
    """N-5: dos textos que solo difieren en espacios y saltos tienen CER 0."""
    assert cer_pagina("Primera línea\nSegunda línea", "Primera  línea Segunda\n\nlínea") == 0.0


# --- CER de página y CER promedio ------------------------------------------


def test_cer_pagina_una_sustitucion():
    """N-5: «casa» contra «cosa»: 1 sustitución / 4 caracteres = 0,25."""
    assert cer_pagina("casa", "cosa") == pytest.approx(0.25)


def test_cer_pagina_una_insercion():
    """N-5: «hola mundo» (10) contra «hola mundo!»: 1 inserción / 10 = 0,1."""
    assert cer_pagina("hola mundo", "hola mundo!") == pytest.approx(0.1)


def test_cer_pagina_tilde_cuenta_como_error():
    """N-5: «está» contra «esta»: 1 sustitución / 4 = 0,25."""
    assert cer_pagina("está", "esta") == pytest.approx(0.25)


def test_cer_pagina_vacia_vale_uno():
    """N-5 (caso límite): sin renglones detectados el texto es vacío y el CER es 1."""
    assert cer_pagina("Texto de referencia", "") == 1.0


def test_cer_pagina_referencia_vacia_es_un_error():
    """Sin texto de referencia no se puede dividir: se rechaza con un mensaje claro."""
    with pytest.raises(ValueError, match="referencia"):
        cer_pagina("  \n ", "algo")


def test_cer_promedio_es_la_media_por_pagina_no_ponderada():
    """N-5: página 1 «ab»→«» (CER 1) y página 2 de 10 caracteres sin errores (CER 0).

    Media por página = (1 + 0) / 2 = 0,5. Ponderado por caracteres daría 2/12.
    """
    cers = [cer_pagina("ab", ""), cer_pagina("abcdefghij", "abcdefghij")]

    assert cer_promedio(cers) == pytest.approx(0.5)


def test_cer_promedio_de_tres_paginas():
    """N-5: (0,25 + 0,1 + 0) / 3 = 0,11666…"""
    assert cer_promedio([0.25, 0.1, 0.0]) == pytest.approx(0.35 / 3)


def test_cer_promedio_sin_paginas_es_un_error():
    with pytest.raises(ValueError, match="página"):
        cer_promedio([])


# --- Acierto en caracteres del español -------------------------------------


def test_conjunto_de_caracteres_del_espanol():
    """N-5: los caracteres que se miden son á é í ó ú ñ ü ¿ ¡."""
    assert set(CARACTERES_ESPANOL) == set("áéíóúñü¿¡")


def test_acierto_todos_correctos():
    """N-5: los 9 caracteres reconocidos bien dan 9 de 9."""
    referencia = "á é í ó ú ñ ü ¿ ¡"
    resultado = acierto_espanol(referencia, referencia)

    assert resultado["total"] == {"aciertos": 9, "apariciones": 9, "proporcion": 1.0}
    for caracter in "áéíóúñü¿¡":
        assert resultado["por_caracter"][caracter]["aciertos"] == 1
        assert resultado["por_caracter"][caracter]["apariciones"] == 1


def test_acierto_tildes_borradas():
    """N-5: «camión está aquí» reconocido como «camion esta aqui»: 0 de 3."""
    resultado = acierto_espanol("camión está aquí", "camion esta aqui")

    assert resultado["total"] == {"aciertos": 0, "apariciones": 3, "proporcion": 0.0}
    for caracter in "óáí":
        assert resultado["por_caracter"][caracter] == {
            "aciertos": 0,
            "apariciones": 1,
            "proporcion": 0.0,
        }


def test_acierto_caracteres_sustituidos():
    """N-5: «¿Año?» reconocido como «?Ano?»: ¿ y ñ sustituidos, 0 de 2."""
    resultado = acierto_espanol("¿Año?", "?Ano?")

    assert resultado["por_caracter"]["¿"]["aciertos"] == 0
    assert resultado["por_caracter"]["ñ"]["aciertos"] == 0
    assert resultado["total"]["aciertos"] == 0
    assert resultado["total"]["apariciones"] == 2


def test_acierto_parcial():
    """N-5: «ñandú ¿sí?» → «ñandu ¿si?»: ñ y ¿ bien, ú e í mal: 2 de 4 = 0,5."""
    resultado = acierto_espanol("ñandú ¿sí?", "ñandu ¿si?")

    assert resultado["por_caracter"]["ñ"]["aciertos"] == 1
    assert resultado["por_caracter"]["¿"]["aciertos"] == 1
    assert resultado["por_caracter"]["ú"]["aciertos"] == 0
    assert resultado["por_caracter"]["í"]["aciertos"] == 0
    assert resultado["total"] == {"aciertos": 2, "apariciones": 4, "proporcion": 0.5}


def test_acierto_usa_la_alineacion_y_no_la_posicion_literal():
    """N-5: un prefijo insertado desplaza las posiciones, pero la alineación los encuentra."""
    resultado = acierto_espanol("¡Sí, señor!", "xx ¡Sí, señor!")

    assert resultado["total"] == {"aciertos": 3, "apariciones": 3, "proporcion": 1.0}


def test_acierto_normaliza_antes_de_alinear():
    """N-5: una ñ descompuesta (n + U+0303) en el texto reconocido cuenta como acierto."""
    resultado = acierto_espanol("niño", "niño")

    assert resultado["por_caracter"]["ñ"]["aciertos"] == 1


def test_acierto_caracter_ausente_en_la_referencia():
    """Un carácter que no aparece en la referencia no tiene proporción (None), no 0."""
    resultado = acierto_espanol("casa", "casa")

    assert resultado["por_caracter"]["ü"] == {
        "aciertos": 0,
        "apariciones": 0,
        "proporcion": None,
    }
    assert resultado["total"]["proporcion"] is None


# ===========================================================================
# Elección del ganador y sus marcas (N-6, N-7 y N-8)
# Números de candidato de la spec: 1 línea base, 2 qantev, 3 printed,
# 4 docTR completo, 5 Tesseract.
# ===========================================================================

def m(numero, cer, vram=1.0, tiempo=2.0, motivo=None):
    return Medicion(
        numero=numero,
        nombre=f"candidato {numero}",
        cer_promedio=cer,
        vram_pico_gb=vram,
        tiempo_promedio_s=tiempo,
        motivo_sin_medir=motivo,
    )


def sin_medir(numero, motivo="falló al cargar"):
    return m(numero, None, None, None, motivo)


# --- N-6: elección ----------------------------------------------------------


def test_gana_el_de_menor_cer_entre_los_elegibles():
    """N-6.1."""
    eleccion = elegir([m(1, 0.20), m(2, 0.08), m(3, 0.05)])

    assert eleccion.ganador.numero == 3


def test_se_excluyen_los_que_superan_la_vram_o_el_tiempo():
    """N-6.1: más de 2,5 GB o más de 10 s por página no son elegibles."""
    eleccion = elegir(
        [
            m(1, 0.01, vram=2.51),
            m(2, 0.02, tiempo=10.01),
            m(3, 0.09),
        ]
    )

    assert eleccion.ganador.numero == 3
    assert set(eleccion.excluidos) == {1, 2}
    assert "VRAM" in eleccion.excluidos[1]
    assert "tiempo" in eleccion.excluidos[2]


def test_los_limites_exactos_son_elegibles():
    """N-6.1: «≤ 2,5 GB» y «≤ 10 s» incluyen el valor exacto."""
    eleccion = elegir([m(1, 0.05, vram=2.5, tiempo=10.0)])

    assert eleccion.ganador.numero == 1


def test_un_candidato_sin_medir_no_es_elegible():
    """N-5 (fallos) y N-6: el que quedó «sin medir» no entra en la elección."""
    eleccion = elegir([sin_medir(3, "Tika no responde"), m(1, 0.30)])

    assert eleccion.ganador.numero == 1
    assert "Tika no responde" in eleccion.excluidos[3]


def test_empate_por_cer_se_decide_por_menor_vram():
    """N-6.2: 0,050 y 0,054 difieren en ≤ 0,005: gana el de menor VRAM."""
    eleccion = elegir([m(1, 0.050, vram=2.0, tiempo=1.0), m(2, 0.054, vram=1.0, tiempo=5.0)])

    assert eleccion.ganador.numero == 2


def test_empate_por_cer_y_vram_se_decide_por_menor_tiempo():
    """N-6.2: misma VRAM: gana el de menor tiempo."""
    eleccion = elegir([m(1, 0.050, vram=1.5, tiempo=4.0), m(2, 0.053, vram=1.5, tiempo=3.0)])

    assert eleccion.ganador.numero == 2


def test_diferencia_de_exactamente_0005_es_empate():
    """N-6.2: «0,005 o menos» incluye 0,005 (0,100 contra 0,105)."""
    eleccion = elegir([m(1, 0.100, vram=2.0), m(2, 0.105, vram=1.0)])

    assert eleccion.ganador.numero == 2


def test_diferencia_mayor_a_0005_gana_el_de_menor_cer():
    """N-6.2: 0,100 contra 0,106 no es empate, aunque el segundo use menos VRAM."""
    eleccion = elegir([m(1, 0.100, vram=2.0), m(2, 0.106, vram=0.5)])

    assert eleccion.ganador.numero == 1


def test_sin_elegibles_no_hay_ganador_y_queda_la_brecha_de_cada_uno():
    """N-6.5: nadie cumple VRAM y tiempo: no hay ganador y se documenta cada brecha."""
    eleccion = elegir([m(1, 0.30, vram=3.0), m(2, 0.05, tiempo=12.0)])

    assert eleccion.ganador is None
    assert eleccion.listo_para_integrar is False
    assert eleccion.brechas[1]["vram_gb"] == pytest.approx(0.5)
    assert eleccion.brechas[1]["cer"] == pytest.approx(0.20)
    assert eleccion.brechas[2] == {"tiempo_s": pytest.approx(2.0)}


def test_sin_ningun_candidato_medido_no_hay_ganador():
    eleccion = elegir([sin_medir(1), sin_medir(4)])

    assert eleccion.ganador is None
    assert eleccion.brechas == {}


def test_ganador_con_cer_hasta_010_queda_listo():
    """N-6.3: CER promedio ≤ 0,10 (incluido 0,10) queda «listo para integrar»."""
    eleccion = elegir([m(3, 0.10)])

    assert eleccion.listo_para_integrar is True
    assert 3 not in eleccion.brechas


def test_ganador_con_cer_mayor_a_010_se_elige_sin_quedar_listo():
    """N-6.4: se elige igual, sin la marca, y con la brecha documentada."""
    eleccion = elegir([m(1, 0.25), m(3, 0.15)])

    assert eleccion.ganador.numero == 3
    assert eleccion.listo_para_integrar is False
    assert eleccion.brechas[3] == {"cer": pytest.approx(0.05)}


# --- N-7: proponer RF-09 «Parcial» ------------------------------------------


def test_n7_no_aparece_si_la_linea_base_gana_y_queda_lista():
    eleccion = elegir([m(1, 0.08), m(3, 0.20)])

    assert eleccion.proponer_rf09_parcial is False


def test_n7_no_aparece_si_la_linea_base_cumple_el_criterio_aunque_pierda():
    """N-7: la línea base cumple VRAM, tiempo y CER ≤ 0,10; otro es mejor."""
    eleccion = elegir([m(1, 0.09), m(3, 0.03)])

    assert eleccion.ganador.numero == 3
    assert eleccion.proponer_rf09_parcial is False


@pytest.mark.parametrize(
    "linea_base",
    [
        m(1, 0.25),  # CER > 0,10
        m(1, 0.05, vram=3.0),  # supera la VRAM
        m(1, 0.05, tiempo=11.0),  # supera el tiempo
        sin_medir(1),  # no se pudo medir
    ],
    ids=["cer", "vram", "tiempo", "sin_medir"],
)
def test_n7_aparece_si_la_linea_base_no_queda_lista(linea_base):
    eleccion = elegir([linea_base, m(3, 0.04)])

    assert eleccion.proponer_rf09_parcial is True


def test_n7_aparece_si_la_linea_base_no_esta_entre_los_candidatos():
    eleccion = elegir([m(3, 0.04)])

    assert eleccion.proponer_rf09_parcial is True


# --- N-8: cambio de requisito -----------------------------------------------


@pytest.mark.parametrize("numero", [4, 5], ids=["doctr", "tesseract"])
def test_n8_aparece_si_gana_doctr_o_tesseract(numero):
    eleccion = elegir([m(1, 0.30), m(numero, 0.02)])

    assert eleccion.ganador.numero == numero
    assert eleccion.cambio_de_requisito is True


@pytest.mark.parametrize("numero", [1, 2, 3])
def test_n8_no_aparece_si_gana_un_trocr(numero):
    eleccion = elegir([m(numero, 0.02), m(5, 0.30)])

    assert eleccion.ganador.numero == numero
    assert eleccion.cambio_de_requisito is False


def test_n8_no_aparece_sin_ganador():
    eleccion = elegir([m(4, 0.02, vram=4.0)])

    assert eleccion.ganador is None
    assert eleccion.cambio_de_requisito is False


# --- Acierto de todo el set (N-5) ------------------------------------------


def test_sumar_aciertos_de_varias_paginas():
    """N-5: el acierto del candidato suma las apariciones de todas sus páginas."""
    from metricas_impreso import sumar_aciertos

    total = sumar_aciertos(
        [acierto_espanol("ñandú ¿sí?", "ñandu ¿si?"), acierto_espanol("niño", "niño")]
    )

    assert total["por_caracter"]["ñ"] == {"aciertos": 2, "apariciones": 2, "proporcion": 1.0}
    assert total["total"] == {"aciertos": 3, "apariciones": 5, "proporcion": 0.6}


def test_sumar_aciertos_sin_paginas():
    from metricas_impreso import sumar_aciertos

    assert sumar_aciertos([])["total"]["proporcion"] is None
