"""Pruebas de T3 (spec 002, RA-02.1): el resumen en español, el XPASS estricto y el código de salida.

Reciben un diccionario de estadísticas como el de `terminalreporter.stats` de pytest, con
informes simulados (`SimpleNamespace`): no ejecutan ninguna prueba ni usan servicios.
"""
import re
from types import SimpleNamespace

import pytest

from tests.soporte.resumen import calcular_resumen, codigo_salida, texto_resumen


def _informe(nodeid, longrepr=None):
    return SimpleNamespace(nodeid=nodeid, longrepr=longrepr)


def _omitido(nodeid, motivo):
    # pytest guarda las omitidas como (archivo, línea, "Skipped: motivo").
    return _informe(nodeid, ("/app/tests/x.py", 7, f"Skipped: {motivo}"))


ESTADISTICAS_MIXTAS = {
    "passed": [_informe("a"), _informe("b"), _informe("c")],
    "failed": [_informe("f1", "AssertionError")],
    "xfailed": [_informe("x1"), _informe("x2")],
    "xpassed": [],
    "error": [_informe("e1")],
    "skipped": [_omitido("s1", "no hay GPU")],
    "": [_informe("setup"), _informe("setup2")],  # clave vacía que pytest también usa; se ignora
    "deselected": [_informe("d1")],
}


def _linea(texto, etiqueta):
    """Valor numérico de la línea «<etiqueta>: N» del resumen."""
    coincidencia = re.search(rf"^\s*{re.escape(etiqueta)}:\s+(\d+)\s*$", texto, flags=re.MULTILINE)
    assert coincidencia, f"No hay una línea «{etiqueta}: N» en:\n{texto}"
    return int(coincidencia.group(1))


def test_el_resumen_trae_los_seis_contadores_en_espanol():
    """RA-02.1: pasan, fallan, fallos esperados, XPASS, errores de preparación y omitidas."""
    texto = texto_resumen(calcular_resumen(ESTADISTICAS_MIXTAS))
    assert _linea(texto, "Pasan") == 3
    assert _linea(texto, "Fallan") == 1
    assert _linea(texto, "Fallos esperados") == 2
    assert _linea(texto, "XPASS (fallos esperados que pasan)") == 0
    assert _linea(texto, "Errores de preparación") == 1
    assert _linea(texto, "Omitidas") == 1


def test_el_resumen_muestra_el_motivo_de_cada_omitida():
    """RA-02.1: las omitidas se muestran con su motivo (sin el prefijo «Skipped:» de pytest)."""
    texto = texto_resumen(calcular_resumen(ESTADISTICAS_MIXTAS))
    assert "s1" in texto and "no hay GPU" in texto
    assert "Skipped:" not in texto


def test_un_resumen_sin_pruebas_muestra_los_seis_contadores_en_cero():
    """RA-02.1: los seis aparecen siempre, aunque no haya nada que contar."""
    texto = texto_resumen(calcular_resumen({}))
    for etiqueta in ("Pasan", "Fallan", "Fallos esperados", "XPASS (fallos esperados que pasan)",
                     "Errores de preparación", "Omitidas"):
        assert _linea(texto, etiqueta) == 0


def test_un_fallo_xpass_estricto_se_cuenta_como_xpass_y_no_como_fallo():
    """RA-02.1: con `xfail_strict`, pytest informa el XPASS como fallo `[XPASS(strict)]`; se reclasifica."""
    estadisticas = {
        "passed": [_informe("p")],
        "failed": [
            _informe("estricto", "[XPASS(strict)] RF-19.1 todavía no se cumple"),
            _informe("de_verdad", "AssertionError: 1 != 2"),
        ],
    }
    resumen = calcular_resumen(estadisticas)
    assert resumen.xpass == 1
    assert resumen.fallan == 1
    texto = texto_resumen(resumen)
    assert _linea(texto, "XPASS (fallos esperados que pasan)") == 1
    assert _linea(texto, "Fallan") == 1


def test_un_xpass_no_estricto_tambien_se_cuenta_como_xpass():
    """RA-02.1: si alguna vez llega en `xpassed`, también cuenta como XPASS."""
    resumen = calcular_resumen({"xpassed": [_informe("x")]})
    assert resumen.xpass == 1 and resumen.fallan == 0


def test_los_fallos_con_longrepr_que_no_es_texto_se_cuentan_como_fallos():
    """RA-02.1: el informe real trae objetos como `longrepr`; solo el texto `[XPASS(strict)]` reclasifica."""
    estadisticas = {"failed": [_informe("f", SimpleNamespace(reprcrash="boom")), _informe("g", None)]}
    resumen = calcular_resumen(estadisticas)
    assert resumen.fallan == 2 and resumen.xpass == 0


@pytest.mark.parametrize(
    "estadisticas, esperado",
    [
        ({"passed": [_informe("a")]}, 0),
        ({}, 0),
        ({"passed": [_informe("a")], "xfailed": [_informe("x")]}, 0),
        # Las omitidas se muestran pero no hacen fallar la corrida.
        ({"passed": [_informe("a")], "skipped": [_omitido("s", "motivo")]}, 0),
        ({"failed": [_informe("f", "AssertionError")]}, 1),
        ({"failed": [_informe("f", "[XPASS(strict)] RF-01.1")]}, 1),
        ({"xpassed": [_informe("x")]}, 1),
        ({"error": [_informe("e")]}, 1),
        ({"passed": [_informe("a")], "skipped": [_omitido("s", "m")], "error": [_informe("e")]}, 1),
    ],
)
def test_el_codigo_de_salida_es_exito_solo_sin_fallos_xpass_ni_errores(estadisticas, esperado):
    """RA-02.1: éxito solo sin fallos, XPASS ni errores de preparación; las omitidas no lo afectan."""
    assert codigo_salida(calcular_resumen(estadisticas)) == esperado


def test_el_texto_dice_si_la_corrida_fue_correcta_o_no():
    """RA-02.1: la última línea del resumen anuncia el resultado en español."""
    correcta = texto_resumen(calcular_resumen({"passed": [_informe("a")]}))
    con_problemas = texto_resumen(calcular_resumen({"failed": [_informe("f", "AssertionError")]}))
    assert "correcta" in correcta.lower().splitlines()[-1]
    assert "con problemas" in con_problemas.lower().splitlines()[-1]


# --- Corrección tras la verificación de T5 (M2): el resumen no debe decir «correcta» si no hubo corrida ---

SIN_PRUEBAS = {}


def _ultima_linea(texto):
    return texto.splitlines()[-1].lower()


def test_con_codigo_de_salida_0_o_1_el_resumen_conserva_su_texto():
    """RA-02.1: con el código 0 o 1 (hubo pruebas) el resultado sigue saliendo de los contadores, como antes."""
    bien = {"passed": [_informe("a")]}
    mal = {"failed": [_informe("f", "AssertionError")]}
    assert texto_resumen(calcular_resumen(bien), 0) == texto_resumen(calcular_resumen(bien))
    assert texto_resumen(calcular_resumen(mal), 1) == texto_resumen(calcular_resumen(mal))
    assert "correcta" in _ultima_linea(texto_resumen(calcular_resumen(bien), 0))
    assert "con problemas" in _ultima_linea(texto_resumen(calcular_resumen(mal), 1))


@pytest.mark.parametrize(
    "codigo, esperado",
    [
        pytest.param(2, "se abortó", id="2-abortada-o-interrumpida"),
        pytest.param(3, "error interno", id="3-error-interno"),
        pytest.param(4, "error de uso", id="4-error-de-uso"),
        pytest.param(5, "no se ejecutó ninguna prueba", id="5-nada-recolectado"),
    ],
)
def test_si_el_codigo_de_salida_no_es_0_ni_1_el_resumen_no_dice_corrida_correcta(codigo, esperado):
    """RA-02.1: con seis ceros y una corrida que no ejecutó pruebas, el resumen NO anuncia éxito y dice qué pasó."""
    texto = texto_resumen(calcular_resumen(SIN_PRUEBAS), codigo)
    assert "correcta" not in texto.lower()
    assert esperado in texto.lower()
    assert f"código de salida {codigo}" in texto
    for etiqueta in ("Pasan", "Fallan", "Fallos esperados", "XPASS (fallos esperados que pasan)",
                     "Errores de preparación", "Omitidas"):
        assert _linea(texto, etiqueta) == 0  # los seis contadores siguen apareciendo


@pytest.mark.parametrize("codigo", [2, 3, 4, 5, 99])
def test_un_codigo_distinto_de_0_y_1_no_es_corrida_correcta_aunque_los_contadores_esten_limpios(codigo):
    """RA-02.1: pasaron algunas pruebas, pero la corrida no terminó bien: no se anuncia éxito."""
    texto = texto_resumen(calcular_resumen({"passed": [_informe("a"), _informe("b")]}), codigo)
    assert "correcta" not in texto.lower()
    assert _linea(texto, "Pasan") == 2


def test_un_codigo_desconocido_se_informa_como_inesperado():
    assert "inesperado" in _ultima_linea(texto_resumen(calcular_resumen(SIN_PRUEBAS), 99))


def test_si_la_corrida_se_aborto_el_resumen_incluye_el_motivo_cuando_se_conoce():
    """RA-02.1: el aborto de una fixture (por ejemplo, Qdrant caído) llega con su mensaje."""
    texto = texto_resumen(calcular_resumen(SIN_PRUEBAS), 2, motivo="Se aborta la suite de pruebas: Qdrant no respondió en 60 segundos")
    assert "Qdrant no respondió" in texto
    assert "correcta" not in texto.lower()


# --- T8 (RA-02.7): si al cerrar la sesión quedaron residuos, el resumen no puede decir «correcta» ---

def test_con_residuos_el_resumen_no_dice_corrida_correcta_aunque_los_contadores_esten_limpios():
    """RA-02.7: el cierre de la sesión hace fallar la corrida si quedaron datos de prueba; el resultado debe decirlo."""
    texto = texto_resumen(calcular_resumen({"passed": [_informe("a")]}), 0, residuos=True)
    assert "correcta" not in texto.lower()
    assert "con problemas" in _ultima_linea(texto) and "sin limpiar" in _ultima_linea(texto)
    assert _linea(texto, "Pasan") == 1


def test_sin_residuos_el_resumen_conserva_su_texto():
    bien = calcular_resumen({"passed": [_informe("a")]})
    assert texto_resumen(bien, 0, residuos=False) == texto_resumen(bien, 0) == texto_resumen(bien)
    assert "correcta" in _ultima_linea(texto_resumen(bien, 0))


def test_con_un_codigo_de_aborto_los_residuos_no_cambian_la_explicacion_del_aborto():
    texto = texto_resumen(calcular_resumen(SIN_PRUEBAS), 2, residuos=True)
    assert "se abortó" in _ultima_linea(texto)


def test_el_codigo_de_salida_acepta_el_enum_de_pytest():
    """pytest entrega `ExitCode` (un `IntEnum`) al gancho del resumen."""
    texto = texto_resumen(calcular_resumen(SIN_PRUEBAS), pytest.ExitCode.NO_TESTS_COLLECTED)
    assert "no se ejecutó ninguna prueba" in texto.lower()
    assert "correcta" not in texto.lower()
