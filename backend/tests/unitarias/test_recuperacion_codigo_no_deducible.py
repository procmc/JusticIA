"""Pruebas de T5 (spec 003b): quien recibe la respuesta de la solicitud no puede deducir el código (RF-03.1 b).

RF-03.1: el código solo se entrega por correo y quien disponga de todo lo que recibió el navegador, sin la clave de firma y
sin leer el correo, no puede confirmar cuál es. Un código son solo 10^6 posibilidades, así que no basta mirar si el código
aparece: hay que recorrerlas TODAS y comprobar que ninguna, ni su forma derivada, coincide con algo de lo observable.

Qué se recorre. Los 1 000 000 de códigos de 6 dígitos, en diez bloques de 100 000 (cada uno de menos de 1 s). Para cada
código se comprueba que ni él ni su `sha256`, `sha256(código + correo)` y `sha256(correo + código)` (ni la primera ni la
segunda mitad de 16 bytes de cada resumen) coinciden con una ventana de lo observable.

Qué es lo observable. Lo que el navegador recibe de la solicitud: el cuerpo en bruto, cada campo, el token partido en sus
dos segmentos y cada pieza decodificada como base64 (alfabeto de URL y estándar) y como hexadecimal. De cada una se toman
todas las ventanas de 6, 16 y 32 bytes y se buscan en conjuntos, así el ciclo de los 10^6 códigos no codifica nada
(ni `hexdigest` ni base64) y cabe en un segundo.

Control positivo, por forma. Una prueba que no encuentra nada podría no estar buscando. Para cada forma (el código en claro,
en base64 y en hexadecimal; cada resumen y su mitad, en base64 y en hexadecimal) se construye una respuesta sintética que SÍ la
contiene en el token, y el mismo barrido tiene que detectarla.

Es determinista: la clave de firma, el correo y la emisión del token son fijos (el código del correo sigue siendo aleatorio),
así la huella no puede tener por azar seis dígitos seguidos. Los datos son inventados.
"""
import asyncio
import base64
import binascii
import hashlib
import time
import types

import pytest

CORREO = "prueba.ana@prueba.invalid"
CLAVE_SINTETICA = "PRUEBA-clave-sintetica-fija-para-las-pruebas-0123456789-abcdef"
EMISION_FIJA = "AbCdEfGhIjKlMnOpQrStUv"  # 22 caracteres, sin dígitos
TAMANOS_DE_VENTANA = (6, 16, 32)
BLOQUES = 10
CODIGOS_POR_BLOQUE = 100_000
LIMITE_POR_BLOQUE = 1.0  # segundos reales


# --- Lo observable y el barrido (puros, sin Redis ni base de datos) ---------------------------------------------------------

def _decodificaciones(pieza: bytes):
    """La pieza tal cual y, si se puede, decodificada como base64 (URL y estándar, con o sin relleno) y como hexadecimal."""
    salidas = [pieza]
    relleno = pieza + b"=" * (-len(pieza) % 4)
    for alfabeto in (b"-_", b"+/"):
        try:
            salidas.append(base64.b64decode(relleno, altchars=alfabeto, validate=True))
        except (binascii.Error, ValueError):
            pass
    try:
        salidas.append(bytes.fromhex(pieza.decode("ascii")))
    except (UnicodeDecodeError, ValueError):
        pass
    return salidas


def observables_de(cuerpo: str, token: str, campos: dict) -> list:
    """Lo que recibe el navegador, como piezas de bytes: el cuerpo en bruto, cada campo y cada segmento del token."""
    piezas = [cuerpo, token, *campos.values(), *token.split(".")]
    return [pieza.encode("utf-8") for pieza in piezas if pieza]


def ventanas_de(observables: list) -> dict:
    """Los conjuntos de todas las ventanas de 6, 16 y 32 bytes de cada observable y de cada una de sus decodificaciones."""
    ventanas = {tamano: set() for tamano in TAMANOS_DE_VENTANA}
    for observable in observables:
        for contenido in _decodificaciones(observable):
            for tamano in TAMANOS_DE_VENTANA:
                for inicio in range(len(contenido) - tamano + 1):
                    ventanas[tamano].add(contenido[inicio:inicio + tamano])
    return ventanas


def barrer(codigos: range, correo: bytes, ventanas: dict) -> list:
    """Los códigos del rango cuya forma (en claro o cualquiera de los tres resúmenes y sus mitades) está en las ventanas.

    Devuelve tuplas `(código, forma)`. Está escrito sin llamadas dentro del ciclo que no sean los tres SHA-256 y las
    búsquedas en conjuntos: es lo que permite recorrer 100 000 códigos en menos de un segundo.
    """
    de6, de16, de32 = ventanas[6], ventanas[16], ventanas[32]
    sha256 = hashlib.sha256
    halladas = []
    for numero in codigos:
        codigo = b"%06d" % numero
        if codigo in de6:
            halladas.append((numero, "código"))
        resumen = sha256(codigo).digest()
        if resumen in de32 or resumen[:16] in de16 or resumen[16:] in de16:
            halladas.append((numero, "sha256(código)"))
        resumen = sha256(codigo + correo).digest()
        if resumen in de32 or resumen[:16] in de16 or resumen[16:] in de16:
            halladas.append((numero, "sha256(código+correo)"))
        resumen = sha256(correo + codigo).digest()
        if resumen in de32 or resumen[:16] in de16 or resumen[16:] in de16:
            halladas.append((numero, "sha256(correo+código)"))
    return halladas


# --- La respuesta real del servicio ---------------------------------------------------------------------------------------------

_respuesta_real = {}


@pytest.fixture
def observables_reales(monkeypatch, redis_controlable):
    """Lo que recibe el navegador de una solicitud real a una cuenta Activa (servicio con repositorio y Redis simulados).

    La clave de firma y la emisión del token son fijas para que la huella (y con ella lo observable) no cambie entre
    corridas; el código que sale por correo sigue siendo aleatorio. La solicitud se hace UNA vez por corrida y los diez
    bloques comparten esa misma respuesta: así, entre todos, recorren los 10^6 códigos contra la misma respuesta y el código
    que esa solicitud emitió cae seguro en uno de ellos. Con una solicitud nueva en cada bloque, una filtración del código
    solo se detectaría en el bloque que justo contuviera el código de esa solicitud.
    """
    if "observables" in _respuesta_real:
        return _respuesta_real["observables"]
    from app.services.recuperacion_service import RecuperacionService
    from app.services.usuario_service import UsuarioService
    from app.utils import recuperacion_codigos as rc

    monkeypatch.setenv("JWT_SECRET_KEY", CLAVE_SINTETICA)
    monkeypatch.setattr(rc, "generar_emision", lambda: EMISION_FIJA)
    cuenta = types.SimpleNamespace(
        CN_Id_usuario="PRUEBA700001", CT_Nombre="PRUEBA", CT_Apellido_uno="Peña", CT_Apellido_dos="Núñez",
        CT_Correo=CORREO, CT_Contrasenna="PRUEBA-resumen-que-no-es-real",
        estado=types.SimpleNamespace(CT_Nombre_estado="Activo"),
    )
    repositorio = types.SimpleNamespace(obtener_usuario_por_correo=lambda db, correo: cuenta)
    servicio = RecuperacionService(usuarios=repositorio, servicio_de_usuarios=UsuarioService())
    respuesta = asyncio.run(servicio.solicitar(None, CORREO)).respuesta
    campos = respuesta.model_dump()
    _respuesta_real["observables"] = observables_de(
        respuesta.model_dump_json(), campos["token"], {n: str(v) for n, v in campos.items()}
    )
    return _respuesta_real["observables"]


@pytest.fixture
def ventanas_reales(observables_reales):
    return ventanas_de(observables_reales)


def test_lo_observable_de_la_respuesta_real_no_tiene_por_azar_seis_digitos_seguidos(observables_reales, ventanas_reales):
    """Precondición de la recorrida: la respuesta real (con la clave, el correo y la emisión fijos) no tiene por azar una
    ventana de seis dígitos, que coincidiría con alguno de los 10^6 códigos sin que haya ninguna filtración. También
    comprueba que lo observable no está vacío (el token existe y tiene sus dos segmentos)."""
    assert len(observables_reales) >= 5
    assert any(len(pieza) == 45 and pieza.count(b".") == 1 for pieza in observables_reales)
    assert not [ventana for ventana in ventanas_reales[6] if ventana.isdigit()]


@pytest.mark.parametrize("bloque", range(BLOQUES), ids=lambda b: f"bloque {b + 1} de {BLOQUES}")
def test_ningun_codigo_ni_su_forma_derivada_coincide_con_lo_que_recibe_el_navegador(bloque, ventanas_reales):
    """RF-03.1 (b): en cada bloque de 100 000 códigos, ninguno (ni su base64 o hexadecimal, ni sus tres resúmenes y mitades)
    coincide con una parte observable de la respuesta; cada bloque tarda menos de 1 s."""
    codigos = range(bloque * CODIGOS_POR_BLOQUE, (bloque + 1) * CODIGOS_POR_BLOQUE)

    inicio = time.perf_counter()
    halladas = barrer(codigos, CORREO.encode("utf-8"), ventanas_reales)
    duracion = time.perf_counter() - inicio

    assert halladas == [], f"se encontraron {len(halladas)} coincidencias con lo observable (formas: {sorted({f for _, f in halladas})})"
    assert len(codigos) == CODIGOS_POR_BLOQUE
    assert duracion < LIMITE_POR_BLOQUE, f"el bloque tardó {duracion:.2f} s (el límite es {LIMITE_POR_BLOQUE} s)"


# --- Control positivo: cada forma, si estuviera en el token, se detecta ---------------------------------------------------------------

# Un código inventado y estable que sale de una etiqueta: ningún código queda escrito en el archivo.
CODIGO_DE_CONTROL = int.from_bytes(hashlib.sha256(b"PRUEBA codigo de control").digest()[:8], "big") % 10 ** 6
_CODIGO = b"%06d" % CODIGO_DE_CONTROL
_CORREO = CORREO.encode("utf-8")
_RESUMENES = {
    "sha256(código)": hashlib.sha256(_CODIGO).digest(),
    "sha256(código+correo)": hashlib.sha256(_CODIGO + _CORREO).digest(),
    "sha256(correo+código)": hashlib.sha256(_CORREO + _CODIGO).digest(),
}


def _formas_de_control():
    """Cada forma que el barrido debe detectar, como `(nombre, forma buscada, bytes que la contienen en el token)`."""
    formas = [
        ("código en claro", "código", _CODIGO),
        ("código en base64", "código", base64.urlsafe_b64encode(_CODIGO)),
        ("código en hexadecimal", "código", _CODIGO.hex().encode()),
    ]
    for nombre, resumen in _RESUMENES.items():
        for parte, bytes_de_la_parte in (("completo", resumen), ("primera mitad", resumen[:16]), ("segunda mitad", resumen[16:])):
            formas.append((f"{nombre} {parte} en hexadecimal", nombre, bytes_de_la_parte.hex().encode()))
            formas.append((f"{nombre} {parte} en base64", nombre, base64.urlsafe_b64encode(bytes_de_la_parte).rstrip(b"=")))
    return formas


@pytest.mark.parametrize("descripcion, forma, segmento", _formas_de_control(), ids=[f[0] for f in _formas_de_control()])
def test_control_positivo_una_respuesta_que_si_contiene_la_forma_se_detecta(descripcion, forma, segmento):
    """Control positivo (por forma): si el segundo segmento del token fuera esta forma del código, el mismo barrido lo
    detecta. Así la recorrida de arriba no pasa en vacío. El token sintético tiene el mismo tamaño de campos que el real."""
    token = "A" * 22 + "." + segmento.decode("ascii")
    cuerpo = '{"success":true,"message":"Si el correo existe","token":"%s"}' % token
    ventanas = ventanas_de(observables_de(cuerpo, token, {"message": "Si el correo existe"}))

    halladas = barrer(range(CODIGO_DE_CONTROL - 20, CODIGO_DE_CONTROL + 20), _CORREO, ventanas)

    assert (CODIGO_DE_CONTROL, forma) in halladas, f"no se detectó «{descripcion}»"
    assert {numero for numero, _ in halladas} == {CODIGO_DE_CONTROL}, "solo debe detectar el código que sí está"


def test_control_positivo_sobre_la_respuesta_real_si_la_emision_llevara_el_resumen_del_codigo(ventanas_reales):
    """Control positivo extremo: la misma respuesta real, con el segundo segmento cambiado por el `sha256` del código en
    base64 (lo que haría un token que guardara el resumen sin clave), SÍ se detecta; con la respuesta real, no."""
    token = "A" * 22 + "." + base64.urlsafe_b64encode(_RESUMENES["sha256(código)"]).rstrip(b"=").decode("ascii")
    ventanas = ventanas_de(observables_de('{"token":"%s"}' % token, token, {}))

    assert barrer(range(CODIGO_DE_CONTROL, CODIGO_DE_CONTROL + 1), _CORREO, ventanas) == [(CODIGO_DE_CONTROL, "sha256(código)")]
    assert barrer(range(CODIGO_DE_CONTROL, CODIGO_DE_CONTROL + 1), _CORREO, ventanas_reales) == []
