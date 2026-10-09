"""Pruebas de T2 (spec 003b): las funciones puras de la recuperación de contraseña.

Cubren RF-03.1 (el código solo se conoce por el correo), RF-03.4 (un correo, una huella), RF-03.12 (el correo se
normaliza y se valida), RF-03.21 (tokens de la misma forma, sin datos de la cuenta) y RF-03.24 (el vínculo con la
cuenta). Son funciones sin Redis ni base de datos: reciben claves derivadas y devuelven textos. Los códigos, claves
y correos son inventados (prefijo `prueba`, dominios `.invalid`) y no se imprimen.
"""
import ast
import hashlib
import inspect
import re
import secrets

import pytest

from app.utils import clave_firma
from app.utils import recuperacion_codigos as rc

ALFABETO_URL = re.compile(r"[A-Za-z0-9_-]+")


@pytest.fixture
def claves():
    """Las cuatro claves derivadas de un secreto generado por la prueba."""
    return rc.derivar_claves_de_recuperacion(secrets.token_hex(32))


def _clave(proposito: str) -> bytes:
    return clave_firma.derivar_clave(secrets.token_hex(32), proposito)


# --- Normalización y validación de la entrada (RF-03.12) ---------------------------------------------

@pytest.mark.parametrize("crudo, esperado", [
    ("Ana@Correo.cr ", "ana@correo.cr"),
    (" ANA@CORREO.CR", "ana@correo.cr"),
    ("\tana@correo.cr\n", "ana@correo.cr"),
    ("ana@correo.cr", "ana@correo.cr"),
    ("", ""),
    (None, ""),
])
def test_normalizar_correo_recorta_y_pasa_a_minusculas(crudo, esperado):
    """RF-03.12: mayúsculas y espacios alrededor no cambian de qué correo se trata."""
    assert rc.normalizar_correo(crudo) == esperado


@pytest.mark.parametrize("correo", [
    "ana@correo.cr",
    "ana.perez+tema@sub.correo.go.cr",
    "peña@correo.cr",
    "a@b.cr",
    "a" * (100 - len("@correo.cr")) + "@correo.cr",
])
def test_es_correo_valido_acepta_correos_bien_formados_de_hasta_100_caracteres(correo):
    """RF-03.12: un correo con una sola arroba, dominio con punto y sin espacios, de hasta 100 caracteres, es válido."""
    assert len(correo) <= 100
    assert rc.es_correo_valido(correo) is True


@pytest.mark.parametrize("correo", [
    "",
    "   ",
    "a" * (101 - len("@correo.cr")) + "@correo.cr",
    "sin-arroba.cr",
    "a@@correo.cr",
    "a@b@correo.cr",
    "ana perez@correo.cr",
    "ana@cor reo.cr",
    "ana@correo",
    "ana@.cr",
    "ana@correo.",
    "ana@correo..cr",
    "@correo.cr",
    "ana@",
    "ana@correo.cr\n",
    "ana@co\nrreo.cr",
    None,
    12345,
    ["ana@correo.cr"],
])
def test_es_correo_valido_rechaza_la_entrada_invalida(correo):
    """RF-03.12: vacío, de 101 caracteres, sin arroba, con dos, con espacios internos o sin punto en el dominio → inválido."""
    assert rc.es_correo_valido(correo) is False


def test_el_caso_de_101_caracteres_del_ejemplo_tiene_de_verdad_101():
    """RF-03.12: guarda de la prueba anterior, para que el caso límite no se mueva sin que se note."""
    assert len("a" * (101 - len("@correo.cr")) + "@correo.cr") == 101


@pytest.mark.parametrize("codigo", ["123456", "000000", "012345", "999999"])
def test_es_codigo_valido_acepta_seis_digitos_con_ceros_a_la_izquierda(codigo):
    """RF-03.9: un código son exactamente 6 dígitos ASCII (los ceros a la izquierda cuentan)."""
    assert rc.es_codigo_valido(codigo) is True


@pytest.mark.parametrize("codigo", [
    "", "123", "12345", "1234567", "12345a", " 12345", "12345 ", "123456\n", "12-456",
    "１２３４５６",   # dígitos de ancho completo
    "١٢٣٤٥٦",       # dígitos arábigo-índicos
    None, 123456, 12.5, b"123456",
])
def test_es_codigo_valido_rechaza_lo_que_no_son_seis_digitos_ascii(codigo):
    """RF-03.9: 3 o 7 dígitos, letras, espacios, otros tipos y dígitos no ASCII no son un código y no consumen intento."""
    assert rc.es_codigo_valido(codigo) is False


# --- Huella del correo (RF-03.4, RF-03.12) ------------------------------------------------------------

def test_la_huella_es_igual_para_las_variantes_de_un_mismo_correo(claves):
    """RF-03.12: «Ana@Correo.cr », «ana@correo.cr» y «ANA@CORREO.CR» tienen la misma huella."""
    huellas = {rc.huella_de_correo(claves.huella, correo) for correo in ("Ana@Correo.cr ", "ana@correo.cr", "ANA@CORREO.CR")}

    assert len(huellas) == 1


def test_la_huella_tiene_22_caracteres_url_seguros_y_no_lleva_el_correo(claves):
    """RF-03.4: 16 bytes en base64 «urlsafe» sin relleno son 22 caracteres; no se deduce el correo de ellos."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")

    assert len(huella) == 22
    assert ALFABETO_URL.fullmatch(huella)
    assert huella == rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    assert huella != hashlib.sha256(b"prueba.ana@prueba.invalid").hexdigest()[:22]


def test_la_huella_es_distinta_entre_correos_y_entre_claves(claves):
    """RF-03.4: otro correo o otra clave de huella dan otra huella (y la misma entrada, siempre la misma)."""
    base = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")

    assert rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid") == base
    assert rc.huella_de_correo(claves.huella, "prueba.bea@prueba.invalid") != base
    assert rc.huella_de_correo(_clave("recuperacion/huella"), "prueba.ana@prueba.invalid") != base


# --- Generación del código (RF-03.1) ----------------------------------------------------------------

def test_generar_codigo_usa_secrets_y_rellena_con_ceros_a_la_izquierda(monkeypatch):
    """RF-03.1: el código sale de `secrets.randbelow(10**6)` y siempre tiene 6 dígitos."""
    pedidos = []

    def falso(tope):
        pedidos.append(tope)
        return 7

    monkeypatch.setattr(rc.secrets, "randbelow", falso)

    assert rc.generar_codigo() == "000007"
    assert pedidos == [10 ** 6]


@pytest.mark.parametrize("numero, esperado", [(0, "000000"), (7, "000007"), (123456, "123456"), (999999, "999999")])
def test_generar_codigo_conserva_los_ceros_en_los_extremos(monkeypatch, numero, esperado):
    """RF-03.1: 0 es «000000» y 999999 es «999999»: el rango completo cabe en 6 dígitos."""
    monkeypatch.setattr(rc.secrets, "randbelow", lambda tope: numero)

    assert rc.generar_codigo() == esperado


def test_generar_codigo_real_siempre_da_un_codigo_valido():
    """RF-03.1: sin parchear nada, 300 códigos son todos de 6 dígitos válidos."""
    assert all(rc.es_codigo_valido(rc.generar_codigo()) for _ in range(300))


def test_el_modulo_no_usa_el_generador_pseudoaleatorio_comun():
    """RF-03.1: ni un `import random` ni un `from random`: todo lo impredecible sale de `secrets`."""
    codigo = inspect.getsource(rc)

    assert re.search(r"^\s*(import random|from random)\b", codigo, flags=re.MULTILINE) is None


# --- HMAC del código y del secreto (RF-03.1) ---------------------------------------------------------

def test_hash_de_codigo_es_determinista_hexadecimal_y_depende_de_la_huella_del_codigo_y_de_la_clave(claves):
    """RF-03.1: el HMAC del código (64 hexadecimales) cambia con la huella, con el código y con la clave."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    otra_huella = rc.huella_de_correo(claves.huella, "prueba.bea@prueba.invalid")
    base = rc.hash_de_codigo(claves.codigo, huella, "123456")

    assert re.fullmatch(r"[0-9a-f]{64}", base)
    assert rc.hash_de_codigo(claves.codigo, huella, "123456") == base
    assert rc.hash_de_codigo(claves.codigo, otra_huella, "123456") != base
    assert rc.hash_de_codigo(claves.codigo, huella, "123457") != base
    assert rc.hash_de_codigo(_clave("recuperacion/codigo"), huella, "123456") != base


def test_hash_de_codigo_no_es_un_resumen_sin_clave(claves):
    """RF-03.1: con 10^6 códigos, un SHA-256 simple se invertiría: el HMAC con la clave del servidor no coincide con ninguno de los comunes."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    resultado = rc.hash_de_codigo(claves.codigo, huella, "123456")

    sin_clave = {
        hashlib.sha256(b"123456").hexdigest(),
        hashlib.sha256(("123456" + huella).encode()).hexdigest(),
        hashlib.sha256((huella + "123456").encode()).hexdigest(),
        hashlib.sha256(f"{huella}|123456".encode()).hexdigest(),
        hashlib.sha256(f"{huella}:123456".encode()).hexdigest(),
    }
    assert resultado not in sin_clave


def test_hash_de_secreto_es_determinista_hexadecimal_y_depende_de_la_clave(claves):
    """RF-03.7: el estado guarda solo el HMAC del secreto de la verificación, no el secreto."""
    secreto = rc.generar_secreto()
    base = rc.hash_de_secreto(claves.verificacion, secreto)

    assert re.fullmatch(r"[0-9a-f]{64}", base)
    assert rc.hash_de_secreto(claves.verificacion, secreto) == base
    assert rc.hash_de_secreto(claves.verificacion, rc.generar_secreto()) != base
    assert rc.hash_de_secreto(_clave("recuperacion/verificacion"), secreto) != base
    assert base != hashlib.sha256(secreto.encode()).hexdigest()


# --- Vínculo con la cuenta (RF-03.24) ----------------------------------------------------------------

def _vinculo(clave, cedula="PRUEBA001", correo="prueba.ana@prueba.invalid", estado="Activo", hash_contrasenna="hash-de-prueba-1"):
    return rc.vinculo_de_cuenta(clave, cedula, correo, estado, hash_contrasenna)


def test_el_vinculo_es_determinista_y_cambia_con_cada_uno_de_sus_cuatro_datos(claves):
    """RF-03.24: cédula, correo, estado y hash de la contraseña: si cualquiera cambia, el vínculo cambia."""
    base = _vinculo(claves.vinculo)

    assert re.fullmatch(r"[0-9a-f]{64}", base)
    assert _vinculo(claves.vinculo) == base
    assert _vinculo(claves.vinculo, cedula="PRUEBA002") != base
    assert _vinculo(claves.vinculo, correo="prueba.bea@prueba.invalid") != base
    assert _vinculo(claves.vinculo, estado="Inactivo") != base
    assert _vinculo(claves.vinculo, hash_contrasenna="hash-de-prueba-2") != base
    assert _vinculo(_clave("recuperacion/vinculo")) != base


def test_el_vinculo_normaliza_el_correo(claves):
    """RF-03.24: mayúsculas y espacios del correo no rompen el vínculo."""
    assert _vinculo(claves.vinculo, correo=" Prueba.Ana@PRUEBA.invalid ") == _vinculo(claves.vinculo)


def test_el_vinculo_no_confunde_donde_termina_un_dato_y_empieza_otro(claves):
    """RF-03.24: mover caracteres entre dos datos vecinos no da el mismo vínculo."""
    una = rc.vinculo_de_cuenta(claves.vinculo, "PRUEBA1", "2prueba@prueba.invalid", "Activo", "hash")
    otra = rc.vinculo_de_cuenta(claves.vinculo, "PRUEBA12", "prueba@prueba.invalid", "Activo", "hash")
    tercera = rc.vinculo_de_cuenta(claves.vinculo, "PRUEBA1", "2prueba@prueba.invalid", "Activ", "ohash")

    assert len({una, otra, tercera}) == 3


# --- Tokens (RF-03.21) ---------------------------------------------------------------------------------

def test_la_emision_y_el_secreto_son_aleatorios_url_seguros_y_del_largo_del_plan():
    """RF-03.21: la emisión tiene 22 caracteres y el secreto 43, ambos base64 «urlsafe» y distintos en cada llamada."""
    emisiones = {rc.generar_emision() for _ in range(50)}
    secretos = {rc.generar_secreto() for _ in range(50)}

    assert len(emisiones) == 50 and len(secretos) == 50
    assert all(len(e) == 22 and ALFABETO_URL.fullmatch(e) for e in emisiones)
    assert all(len(s) == 43 and ALFABETO_URL.fullmatch(s) for s in secretos)


def test_el_token_de_la_solicitud_es_huella_punto_emision(claves):
    """RF-03.21: 22 + «.» + 22 = 45 caracteres, sin correo, cédula ni código."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    emision = rc.generar_emision()

    token = rc.crear_token_solicitud(huella, emision)

    assert token == f"{huella}.{emision}"
    assert len(token) == 45
    assert re.fullmatch(r"[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{22}", token)


def test_el_token_de_la_verificacion_es_huella_punto_secreto(claves):
    """RF-03.7: 22 + «.» + 43 = 66 caracteres."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    secreto = rc.generar_secreto()

    token = rc.crear_token_verificacion(huella, secreto)

    assert token == f"{huella}.{secreto}"
    assert len(token) == 66
    assert re.fullmatch(r"[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}", token)


def test_partir_token_devuelve_las_dos_partes_de_cualquiera_de_los_dos_tokens(claves):
    """RF-03.4: `partir_token` recupera la huella y la emisión, o la huella y el secreto."""
    huella = rc.huella_de_correo(claves.huella, "prueba.ana@prueba.invalid")
    emision, secreto = rc.generar_emision(), rc.generar_secreto()

    assert rc.partir_token(rc.crear_token_solicitud(huella, emision)) == (huella, emision)
    assert rc.partir_token(rc.crear_token_verificacion(huella, secreto)) == (huella, secreto)


_H = "A" * 22
_E = "B" * 22
_S = "C" * 43


@pytest.mark.parametrize("token", [
    None, "", " ", 12345, b"abc", ["a.b"],
    "sinpunto",
    f"{_H}.{_E}.{_E}",          # dos puntos
    f".{_E}", f"{_H}.",         # una parte vacía
    f"{'A' * 21}.{_E}",         # huella corta
    f"{'A' * 23}.{_E}",         # huella larga
    f"{_H}.{'B' * 10}",         # segunda parte de otro largo
    f"{_H}.{'B' * 44}",
    f"{_H}.{'B' * 21}",
    f"{'A' * 21}+.{_E}",         # carácter fuera del alfabeto
    f"{'A' * 21}/.{_E}",
    f"{'A' * 21} .{_E}",
    f"{_H}.{'B' * 21}=",         # relleno de base64
    f"{_H}.{'B' * 21}\n",
    f" {_H}.{_E}",
    f"{_H}.{_E} ",
    f"{'Á' * 22}.{_E}",          # letras fuera de ASCII
    "A" * 5000,
    (_H + "." + _E) * 100,
])
def test_partir_token_rechaza_lo_mal_formado(token):
    """RF-03.4: un token con otro formato es «no reconocido» (`None`), nunca una excepción."""
    assert rc.partir_token(token) is None


# --- Las claves de la recuperación -------------------------------------------------------------------------

def test_las_cuatro_claves_son_distintas_entre_si_y_de_la_clave_de_firma():
    """RNF-07.3 / RF-03.1: huella, código, verificación y vínculo usan claves derivadas distintas, ninguna la de las sesiones."""
    secreto = secrets.token_hex(32)

    derivadas = rc.derivar_claves_de_recuperacion(secreto)
    cuatro = [derivadas.huella, derivadas.codigo, derivadas.verificacion, derivadas.vinculo]

    assert len(set(cuatro)) == 4
    assert secreto.encode() not in cuatro
    assert derivadas.huella == clave_firma.derivar_clave(secreto, "recuperacion/huella")
    assert derivadas.codigo == clave_firma.derivar_clave(secreto, "recuperacion/codigo")
    assert derivadas.verificacion == clave_firma.derivar_clave(secreto, "recuperacion/verificacion")
    assert derivadas.vinculo == clave_firma.derivar_clave(secreto, "recuperacion/vinculo")


def test_las_claves_no_salen_en_el_repr():
    """RNF-08.1: si el objeto de claves llega a un registro o a una traza, no muestra los bytes."""
    derivadas = rc.derivar_claves_de_recuperacion(secrets.token_hex(32))

    texto = repr(derivadas) + str(derivadas)

    for clave in (derivadas.huella, derivadas.codigo, derivadas.verificacion, derivadas.vinculo):
        assert repr(clave) not in texto and clave.hex() not in texto


# --- Pureza del módulo -----------------------------------------------------------------------------------

def test_el_modulo_solo_importa_la_biblioteca_estandar_y_la_clave_de_firma():
    """Plan §2: funciones puras, sin Redis, sin base de datos ni librerías nuevas."""
    arbol = ast.parse(inspect.getsource(rc))
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            importados.add(nodo.module or "")

    permitidos = {"base64", "dataclasses", "hashlib", "hmac", "re", "secrets", "typing", "__future__", "app.utils",
                  "app.utils.clave_firma"}
    assert importados <= permitidos, f"importa módulos no previstos: {sorted(importados - permitidos)}"
