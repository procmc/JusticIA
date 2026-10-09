"""Pruebas de T4 (spec 003a, RNF-08.2): enmascarar los correos electrónicos antes de escribirlos en un registro.

El correo de una persona es un dato personal: en los registros del servidor solo debe verse la primera
letra del usuario y el dominio (`a***@dominio.cr`). Datos inventados (prefijo `PRUEBA`, dominios `.invalid`).
"""
import pytest


@pytest.mark.parametrize("correo, esperado", [
    ("persona@dominio.cr", "p***@dominio.cr"),
    ("a@dominio.cr", "a***@dominio.cr"),
    ("nombre.apellido+etiqueta@sub.dominio.go.cr", "n***@sub.dominio.go.cr"),
    ("peña@dominio.cr", "p***@dominio.cr"),
])
def test_enmascarar_correo_deja_la_primera_letra_y_el_dominio(correo, esperado):
    """RNF-08.2: la forma del enmascarado es `p***@dominio`."""
    from app.utils.enmascarar import enmascarar_correo

    assert enmascarar_correo(correo) == esperado


def test_enmascarar_correo_conserva_las_mayusculas_tal_como_vienen():
    """RNF-08.2: no se cambia la capitalización de la primera letra ni del dominio."""
    from app.utils.enmascarar import enmascarar_correo

    assert enmascarar_correo("Persona@Dominio.CR") == "P***@Dominio.CR"


@pytest.mark.parametrize("valor", ["no-es-un-correo", "", "   ", None])
def test_enmascarar_correo_sin_arroba_se_omite_por_completo(valor):
    """RNF-08.2: lo que no tiene forma de correo no se deja ver (podría ser otro dato personal)."""
    from app.utils.enmascarar import enmascarar_correo

    assert enmascarar_correo(valor) == "***"


def test_enmascarar_correo_sin_usuario_solo_deja_el_dominio():
    from app.utils.enmascarar import enmascarar_correo

    assert enmascarar_correo("@dominio.cr") == "***@dominio.cr"


def test_enmascarar_correo_con_varias_arrobas_usa_la_ultima_como_separador():
    from app.utils.enmascarar import enmascarar_correo

    assert enmascarar_correo("a@b@dominio.cr") == "a***@dominio.cr"


def test_enmascarar_correos_en_texto_enmascara_todos_los_correos_de_un_texto():
    """RNF-08.2: un texto con varios correos (como el de la bitácora) sale sin ninguno completo."""
    from app.utils.enmascarar import enmascarar_correos_en_texto

    texto = "El usuario Ana@Uno.invalid reseteó a persona.prueba@sub.dominio.invalid; copia a otro+x@tres.go.cr."
    resultado = enmascarar_correos_en_texto(texto)

    assert resultado == "El usuario A***@Uno.invalid reseteó a p***@sub.dominio.invalid; copia a o***@tres.go.cr."
    for completo in ("Ana@Uno.invalid", "persona.prueba@sub.dominio.invalid", "otro+x@tres.go.cr"):
        assert completo not in resultado


def test_enmascarar_correos_en_texto_no_se_lleva_la_puntuacion_ni_los_signos_vecinos():
    from app.utils.enmascarar import enmascarar_correos_en_texto

    assert enmascarar_correos_en_texto("Hola <a@x.invalid>, (b@y.invalid).") == "Hola <a***@x.invalid>, (b***@y.invalid)."


def test_enmascarar_correos_en_texto_deja_igual_lo_que_no_tiene_correos():
    from app.utils.enmascarar import enmascarar_correos_en_texto

    assert enmascarar_correos_en_texto("Inicio de sesión del usuario 1-0000-0000") == "Inicio de sesión del usuario 1-0000-0000"
    assert enmascarar_correos_en_texto("") == ""
    assert enmascarar_correos_en_texto(None) == ""


def test_enmascarar_correos_en_texto_es_idempotente():
    """Enmascarar dos veces (un texto ya enmascarado que pasa por otro punto) no lo daña."""
    from app.utils.enmascarar import enmascarar_correos_en_texto

    una_vez = enmascarar_correos_en_texto("persona@dominio.invalid")
    assert enmascarar_correos_en_texto(una_vez) == una_vez == "p***@dominio.invalid"
