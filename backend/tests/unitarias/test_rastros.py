"""Pruebas de T5 (spec 003a) del auxiliar `tests/soporte/rastros.py`: la búsqueda de un secreto en los rastros (RNF-08.1).

La búsqueda es la que usan las pruebas de los flujos de correo para comprobar que una contraseña temporal o un correo
completo no quedó en la salida, los registros, la bitácora ni las respuestas. Aquí se prueba el propio auxiliar:
encuentra el valor en cada fuente, falla SIN mostrar el valor y no pasa «en vacío» (una búsqueda sin valor o sin nada
donde buscar no prueba nada). Los valores son inventados (prefijo `PRUEBA`).
"""
import pytest

from tests.soporte import rastros
from tests.soporte.datos import Contrasena

SECRETO = "PRUEBA-secreto-8841Zq"


@pytest.mark.parametrize("nombre, contenido", [
    pytest.param("salida", f"linea 1\nvalor={SECRETO}\n", id="salida"),
    pytest.param("registros", f"WARNING app Correo enviado, clave {SECRETO}", id="registros"),
    pytest.param("bitacora", [f"Inicio de sesión {SECRETO}", "otra fila"], id="bitacora-filas"),
    pytest.param("respuestas", {"detalle": f"error con {SECRETO}"}, id="respuestas-json"),
    pytest.param("respuestas", [b"cuerpo ", f"con {SECRETO}".encode("utf-8")], id="respuestas-bytes"),
])
def test_encuentra_el_valor_en_cada_fuente(nombre, contenido):
    """RNF-08.1: el valor se encuentra en la salida, los registros, las filas de bitácora y las respuestas (texto, JSON o bytes)."""
    fuentes = {"salida": "nada", "registros": "nada", "bitacora": ["nada"], "respuestas": ["nada"]}
    fuentes[nombre] = contenido

    assert rastros.encontrar_en_rastros(SECRETO, **fuentes) == [nombre]


def test_no_encuentra_lo_que_no_esta():
    """RNF-08.1: control negativo; sin el valor en ninguna fuente, la lista de hallazgos queda vacía y `buscar_en_rastros` no falla."""
    fuentes = {"salida": "texto sin secretos", "registros": "WARNING algo", "bitacora": ["fila"], "respuestas": ["{}"]}

    assert rastros.encontrar_en_rastros(SECRETO, **fuentes) == []
    rastros.buscar_en_rastros(SECRETO, **fuentes)


def test_nombra_todas_las_fuentes_donde_lo_encontro():
    """RNF-08.1: el hallazgo lista cada fuente, en el orden en que se dieron."""
    hallazgos = rastros.encontrar_en_rastros(SECRETO, salida=SECRETO, registros="limpio", respuestas=[SECRETO])

    assert hallazgos == ["salida", "respuestas"]


def test_falla_nombrando_las_fuentes_y_sin_mostrar_el_valor():
    """RNF-08.1: si lo encuentra, falla diciendo dónde, y ni el mensaje ni su representación contienen el valor."""
    with pytest.raises(pytest.fail.Exception) as error:
        rastros.buscar_en_rastros(Contrasena(SECRETO), salida=f"x {SECRETO}", registros=f"y {SECRETO}", bitacora=["limpia"])

    mensaje = str(error.value)
    assert "salida" in mensaje and "registros" in mensaje
    assert "bitacora" not in mensaje
    assert SECRETO not in mensaje
    assert SECRETO not in repr(error.value)


@pytest.mark.parametrize("valor", ["", None])
def test_un_valor_vacio_no_pasa_en_vacio(valor):
    """RNF-08.1: un valor vacío «está» en cualquier texto; la búsqueda se niega en vez de pasar o fallar sin sentido."""
    with pytest.raises(ValueError):
        rastros.buscar_en_rastros(valor, salida="algo")
    with pytest.raises(ValueError):
        rastros.encontrar_en_rastros(valor, salida="algo")


def test_sin_ninguna_fuente_no_pasa_en_vacio():
    """RNF-08.1: buscar en nada no prueba nada: sin ninguna fuente es un error de la prueba y no un «limpio»."""
    with pytest.raises(ValueError):
        rastros.buscar_en_rastros(SECRETO)
    with pytest.raises(ValueError):
        rastros.encontrar_en_rastros(SECRETO)


def test_una_fuente_vacia_no_impide_buscar_en_las_demas():
    """RNF-08.1: la salida puede estar vacía (el flujo no imprimió nada) mientras otra fuente tenga contenido."""
    assert rastros.encontrar_en_rastros(SECRETO, salida="", registros=f"con {SECRETO}") == ["registros"]


def test_fuentes_vacias_dan_limpio_y_el_control_positivo_es_de_quien_llama():
    """RNF-08.1: un flujo que no escribió nada en ninguna fuente no es un error del auxiliar; quien llama debe agregar su
    control positivo (el valor sí está donde debe estar) para saber que la captura funciona."""
    assert rastros.encontrar_en_rastros(SECRETO, salida="", registros="", bitacora=[], respuestas=None) == []


# --- valor_tras: sacar de un correo el valor que la prueba va a buscar -------------------------------------------------

def test_valor_tras_extrae_el_valor_que_sigue_al_marcador_y_lo_oculta():
    """RNF-08.1: lee la contraseña que sigue a «contraseña de acceso es:» y la devuelve como `Contrasena` (su repr no la muestra)."""
    texto = f"Hola.\nTu contraseña de acceso es: {SECRETO}\nCámbiala al entrar."

    valor = rastros.valor_tras(texto, "contraseña de acceso es:", patron=r"[A-Za-z0-9\-]+")

    assert valor == SECRETO
    assert isinstance(valor, Contrasena)
    assert SECRETO not in repr(valor)


def test_valor_tras_por_omision_toma_letras_y_numeros_y_se_detiene_en_el_marcado():
    """RNF-08.1: en un cuerpo HTML el valor termina donde empieza la siguiente etiqueta."""
    html = '<div class="password">Zq83RtLm</div><p>Cambie</p>'

    assert rastros.valor_tras(html, '<div class="password">') == "Zq83RtLm"


def test_valor_tras_sin_marcador_falla_sin_repetir_el_texto():
    """RNF-08.1: si el marcador no está, es un error de la prueba que no vuelca el contenido del correo."""
    with pytest.raises(LookupError) as error:
        rastros.valor_tras(f"cuerpo con {SECRETO}", "marcador que no existe")

    assert SECRETO not in str(error.value)
