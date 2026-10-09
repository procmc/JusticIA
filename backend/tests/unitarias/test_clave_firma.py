"""Pruebas de T2 (spec 003b, RNF-07.3 y RNF-07.4): la clave de firma de la recuperación de contraseña.

La recuperación solo funciona con una clave de firma fuerte: 32 caracteres o más, 12 o más distintos y que
no sea un valor de respaldo conocido (el que trae el código o el marcador del archivo de ejemplo). Estas
pruebas comprueban esas reglas, que el motivo y los registros nunca muestren el valor, la derivación de claves
por propósito y el archivo de ejemplo (`backend/.env.example`, que se lee donde está dentro del contenedor y se
omite diciendo por qué si no está).

Ninguna clave real ni escrita en el repositorio: las válidas las genera la propia prueba y las demás son cadenas
sintéticas evidentes («abcdef…» repetido). La lista de valores conocidos se lee del sistema, no de un archivo.
"""
import base64
import hashlib
import hmac
import logging
import os
import re
import secrets
from pathlib import Path

import pytest
from dotenv import dotenv_values

from app.utils import clave_firma as cf
from tests.soporte.configuracion import VARIABLES_DESARROLLO, construir_configuracion

RAIZ_DEL_BACKEND = Path(__file__).resolve().parents[2]
RUTA_DEL_EJEMPLO = RAIZ_DEL_BACKEND / ".env.example"
ALFABETO = "abcdefghijklmnopqrstuvwxyz"
PROPOSITOS = ("recuperacion/huella", "recuperacion/codigo", "recuperacion/verificacion", "recuperacion/vinculo")


def _cadena(largo: int, distintos: int) -> str:
    """Cadena sintética de `largo` caracteres con exactamente `distintos` caracteres distintos (ciclo del alfabeto)."""
    assert 1 <= distintos <= len(ALFABETO) and largo >= distintos
    return (ALFABETO[:distintos] * largo)[:largo]


def _es_fuerte(valor: str) -> bool:
    return len(valor) >= 32 and len(set(valor)) >= 12


# --- RNF-07.3: falta -------------------------------------------------------------------------------

@pytest.mark.parametrize("valor", [None, "", "   ", "\t\n"])
def test_clave_ausente_es_rechazada_con_el_motivo_ausente(valor):
    """RNF-07.3: si la clave falta (no definida, vacía o solo espacios), el motivo es «ausente»."""
    resultado = cf.evaluar_clave_firma(valor)

    assert resultado.valida is False
    assert resultado.motivo == cf.MOTIVO_AUSENTE == "ausente"


# --- RNF-07.3: valores de respaldo conocidos -------------------------------------------------------

def test_la_lista_de_respaldos_conocidos_no_esta_vacia_y_incluye_alguno_fuerte():
    """RNF-07.3: la lista existe y alguno de sus valores cumpliría la regla de fuerza (para que el rechazo no dependa de ella)."""
    assert len(cf.VALORES_DE_RESPALDO_CONOCIDOS) >= 2
    assert any(_es_fuerte(valor) for valor in cf.VALORES_DE_RESPALDO_CONOCIDOS), (
        "se esperaba al menos un valor conocido que por sí solo pasaría la regla de fuerza")


@pytest.mark.parametrize("valor", sorted(cf.VALORES_DE_RESPALDO_CONOCIDOS))
def test_cada_valor_de_respaldo_conocido_es_rechazado_aunque_sea_fuerte(valor):
    """RNF-07.3: cada valor de la lista del sistema (el respaldo del código, el marcador del ejemplo…) se rechaza como respaldo."""
    resultado = cf.evaluar_clave_firma(valor)

    assert resultado.valida is False
    assert resultado.motivo == cf.MOTIVO_RESPALDO == "valor de respaldo conocido"


@pytest.mark.parametrize("valor", sorted(cf.VALORES_DE_RESPALDO_CONOCIDOS))
def test_el_respaldo_conocido_se_reconoce_con_espacios_y_otras_mayusculas(valor):
    """RNF-07.3: un respaldo conocido con espacios alrededor o en mayúsculas sigue siendo un respaldo."""
    assert cf.evaluar_clave_firma(f"  {valor.upper()} \n").motivo == cf.MOTIVO_RESPALDO


def test_los_respaldos_literales_del_codigo_estan_en_la_lista():
    """RNF-07.3: todo valor de respaldo escrito en el código como segundo argumento de `os.getenv("JWT_SECRET_KEY", …)` está en la lista."""
    patron = re.compile(r"""getenv\(\s*["']JWT_SECRET_KEY["']\s*,\s*["']([^"']+)["']\s*\)""")
    encontrados = []
    for ruta in (RAIZ_DEL_BACKEND / "app" / "services" / "auth_service.py", RAIZ_DEL_BACKEND / "app" / "routes" / "auth.py"):
        if not ruta.is_file():
            pytest.skip(f"El archivo {ruta} no está en el contenedor; no se pueden leer los respaldos del código.")
        encontrados += patron.findall(ruta.read_text(encoding="utf-8"))

    assert encontrados, "no se encontró ningún respaldo literal: la búsqueda estaría en vacío"
    assert [valor for valor in encontrados if valor not in cf.VALORES_DE_RESPALDO_CONOCIDOS] == []


# --- RNF-07.3: fuerza -------------------------------------------------------------------------------

@pytest.mark.parametrize("distintos", [12, 20, 26])
def test_31_caracteres_son_debiles_aunque_tengan_12_o_mas_distintos(distintos):
    """RNF-07.3: 31 caracteres con 12 o más distintos → débil por largo."""
    resultado = cf.evaluar_clave_firma(_cadena(31, distintos))

    assert resultado.valida is False
    assert resultado.motivo == cf.MOTIVO_CORTA == "débil: menos de 32 caracteres"


def test_32_caracteres_con_11_distintos_son_debiles():
    """RNF-07.3: 32 caracteres con 11 distintos → débil por variedad."""
    resultado = cf.evaluar_clave_firma(_cadena(32, 11))

    assert resultado.valida is False
    assert resultado.motivo == cf.MOTIVO_POCO_VARIADA == "débil: menos de 12 caracteres distintos"


@pytest.mark.parametrize("largo, distintos", [(32, 12), (32, 26), (33, 12), (64, 12)])
def test_32_o_mas_caracteres_con_12_o_mas_distintos_son_validos(largo, distintos):
    """RNF-07.3: el límite inferior exacto (32 y 12) y lo que está por encima se aceptan."""
    resultado = cf.evaluar_clave_firma(_cadena(largo, distintos))

    assert resultado.valida is True
    assert resultado.motivo is None


@pytest.mark.parametrize("caracter, largo", [("a", 10), ("a", 40), ("0", 64), ("x", 200)])
def test_un_caracter_repetido_es_debil(caracter, largo):
    """RNF-07.3: una cadena de un solo carácter repetido se rechaza, sea corta o larga."""
    assert cf.evaluar_clave_firma(caracter * largo).valida is False


def test_una_clave_corta_y_poco_variada_informa_la_regla_del_largo():
    """RNF-07.3: si fallan las dos reglas, el motivo es el primero que falló (el largo)."""
    assert cf.evaluar_clave_firma("a" * 10).motivo == cf.MOTIVO_CORTA


def test_hexadecimal_de_64_generado_por_la_prueba_es_valido():
    """RNF-07.3: lo que produce `openssl rand -hex 32` (64 hexadecimales) habilita la recuperación."""
    assert cf.evaluar_clave_firma(secrets.token_hex(32)).valida is True


def test_base64_de_44_generado_por_la_prueba_es_valido():
    """RNF-07.3: una clave en base64 de 44 caracteres (32 bytes aleatorios) habilita la recuperación."""
    clave = base64.b64encode(secrets.token_bytes(33)).decode()[:44]

    assert len(clave) == 44
    assert cf.evaluar_clave_firma(clave).valida is True


def test_la_clave_que_fija_la_suite_es_valida():
    """RNF-07.3: la clave de firma de la suite (`construir_configuracion`) y la del entorno de esta corrida cumplen la regla."""
    desarrollo = {nombre: "valor-falso" for nombre in VARIABLES_DESARROLLO}
    generada = construir_configuracion(desarrollo)["JWT_SECRET_KEY"]

    assert cf.evaluar_clave_firma(generada).valida is True
    assert cf.evaluar_clave_firma(os.environ.get("JWT_SECRET_KEY")).valida is True


# --- RNF-07.3: nunca el valor ------------------------------------------------------------------------

def _valores_a_evaluar():
    """Un valor por cada resultado posible; el valor es único y fácil de buscar."""
    marca = "PRUEBA" + secrets.token_hex(4)
    return {
        "ausente": None,
        "respaldo": sorted(cf.VALORES_DE_RESPALDO_CONOCIDOS)[0],
        "corta": marca + "-corta",
        "poco variada": "PRUEBA" + "x" * 40,   # 7 caracteres distintos, siempre
        "valida": marca + secrets.token_hex(24),
    }


def test_ni_el_motivo_ni_los_registros_contienen_el_valor_evaluado(caplog):
    """RNF-07.3: `evaluar_clave_firma` no escribe el valor ni en su resultado (ni en su `repr`) ni en el registro del servidor."""
    valores = _valores_a_evaluar()
    with caplog.at_level(logging.DEBUG):
        resultados = {caso: cf.evaluar_clave_firma(valor) for caso, valor in valores.items()}

    for caso, valor in valores.items():
        if valor:
            resultado = resultados[caso]
            assert valor not in str(resultado.motivo), caso
            assert valor not in repr(resultado), caso
            assert valor not in str(resultado), caso
            assert valor not in caplog.text, f"el registro del servidor muestra la clave del caso «{caso}»"


# --- RNF-07.3: lectura del entorno en cada uso -------------------------------------------------------

def test_leer_clave_firma_devuelve_la_clave_valida_del_entorno(monkeypatch):
    """RNF-07.3: con una clave válida en `JWT_SECRET_KEY`, `leer_clave_firma()` la devuelve."""
    clave = secrets.token_hex(32)
    monkeypatch.setenv("JWT_SECRET_KEY", clave)

    assert cf.leer_clave_firma() == clave


def test_leer_clave_firma_lee_el_entorno_en_cada_uso(monkeypatch):
    """RNF-07.3 (decisión 14): cambiar la variable cambia el resultado en la llamada siguiente, sin reiniciar nada."""
    primera, segunda = secrets.token_hex(32), secrets.token_hex(32)
    monkeypatch.setenv("JWT_SECRET_KEY", primera)
    assert cf.leer_clave_firma() == primera
    monkeypatch.setenv("JWT_SECRET_KEY", segunda)
    assert cf.leer_clave_firma() == segunda
    monkeypatch.setenv("JWT_SECRET_KEY", "corta")
    with pytest.raises(cf.ClaveDeFirmaInvalida):
        cf.leer_clave_firma()
    monkeypatch.setenv("JWT_SECRET_KEY", primera)
    assert cf.leer_clave_firma() == primera


def test_leer_clave_firma_ausente_lanza_el_error_con_el_motivo(monkeypatch):
    """RNF-07.3: sin la variable, `leer_clave_firma()` lanza `ClaveDeFirmaInvalida` con el motivo «ausente»."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(cf.ClaveDeFirmaInvalida) as error:
        cf.leer_clave_firma()

    assert error.value.motivo == "ausente"
    assert "JWT_SECRET_KEY" in str(error.value)


@pytest.mark.parametrize("caso", ["respaldo", "corta", "poco variada"])
def test_leer_clave_firma_invalida_no_muestra_el_valor_ni_en_el_error_ni_en_el_registro(monkeypatch, caplog, caso):
    """RNF-07.3: con una clave inválida el error y el registro del servidor traen el nombre de la variable y el motivo, nunca el valor."""
    valor = _valores_a_evaluar()[caso]
    monkeypatch.setenv("JWT_SECRET_KEY", valor)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(cf.ClaveDeFirmaInvalida) as error:
            cf.leer_clave_firma()

    motivo = cf.evaluar_clave_firma(valor).motivo
    assert error.value.motivo == motivo
    for texto in (str(error.value), repr(error.value), caplog.text):
        assert valor not in texto
    assert "JWT_SECRET_KEY" in caplog.text and motivo in caplog.text, "el registro debe nombrar la variable y el motivo"
    assert [r for r in caplog.records if r.levelno >= logging.ERROR], "el rechazo debe quedar como error en el registro"


def test_leer_clave_firma_valida_no_escribe_nada_en_el_registro(monkeypatch, caplog):
    """RNF-07.3: una clave válida no deja ni el valor ni ninguna línea de error en el registro."""
    clave = secrets.token_hex(32)
    monkeypatch.setenv("JWT_SECRET_KEY", clave)

    with caplog.at_level(logging.DEBUG):
        cf.leer_clave_firma()

    assert clave not in caplog.text
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


# --- RNF-07.3: derivación de claves por propósito -----------------------------------------------------

def test_derivar_clave_es_determinista():
    """RNF-07.3: el mismo secreto y el mismo propósito dan siempre la misma clave."""
    secreto = secrets.token_hex(32)

    assert cf.derivar_clave(secreto, PROPOSITOS[0]) == cf.derivar_clave(secreto, PROPOSITOS[0])


def test_derivar_clave_es_distinta_por_proposito_y_distinta_de_la_clave():
    """RNF-07.3: cada propósito da una clave distinta, y ninguna es la clave que firma las sesiones."""
    secreto = secrets.token_hex(32)

    derivadas = [cf.derivar_clave(secreto, proposito) for proposito in PROPOSITOS]

    assert len(set(derivadas)) == len(PROPOSITOS)
    assert secreto.encode() not in derivadas
    assert all(isinstance(d, bytes) and len(d) == 32 for d in derivadas)


def test_derivar_clave_cambia_con_el_secreto():
    """RNF-07.3: dos secretos distintos dan claves derivadas distintas para el mismo propósito."""
    assert cf.derivar_clave(secrets.token_hex(32), PROPOSITOS[0]) != cf.derivar_clave(secrets.token_hex(32), PROPOSITOS[0])


def test_derivar_clave_usa_hmac_con_la_etiqueta_documentada():
    """RNF-07.3 (plan §3.1): la clave es HMAC-SHA256 del secreto sobre `servia/<propósito>/v1`."""
    secreto = secrets.token_hex(32)

    esperada = hmac.new(secreto.encode(), b"servia/recuperacion/huella/v1", hashlib.sha256).digest()

    assert cf.derivar_clave(secreto, "recuperacion/huella") == esperada


def test_derivar_clave_sin_proposito_o_sin_secreto_es_un_error_de_programacion():
    """RNF-07.3: un propósito o un secreto vacío no deriva nada (evita claves derivadas de un texto vacío)."""
    with pytest.raises(ValueError):
        cf.derivar_clave(secrets.token_hex(32), "")
    with pytest.raises(ValueError):
        cf.derivar_clave("", PROPOSITOS[0])


# --- RNF-07.4: archivo de ejemplo ---------------------------------------------------------------------

def _leer_ejemplo():
    if not RUTA_DEL_EJEMPLO.is_file():
        pytest.skip(f"El archivo de ejemplo no está en el contenedor ({RUTA_DEL_EJEMPLO}); lo verifica el revisor en /sdd-validate.")
    return RUTA_DEL_EJEMPLO.read_text(encoding="utf-8")


def test_el_ejemplo_define_jwt_secret_key_con_un_valor_de_la_lista_de_conocidos():
    """RNF-07.4: `.env.example` define `JWT_SECRET_KEY` con un marcador que la validación rechaza como valor de respaldo."""
    _leer_ejemplo()
    variables = dotenv_values(RUTA_DEL_EJEMPLO)

    assert "JWT_SECRET_KEY" in variables, "el ejemplo no define JWT_SECRET_KEY"
    valor = variables["JWT_SECRET_KEY"]
    assert valor in cf.VALORES_DE_RESPALDO_CONOCIDOS, "el valor del ejemplo debe estar en la lista de conocidos"
    assert cf.evaluar_clave_firma(valor).motivo == cf.MOTIVO_RESPALDO


def test_el_ejemplo_ya_no_define_secret_key():
    """RNF-07.4: la variable `SECRET_KEY`, que el sistema no lee, ya no está definida (ni comentada como valor)."""
    texto = _leer_ejemplo()

    assert "SECRET_KEY" not in dotenv_values(RUTA_DEL_EJEMPLO)
    assert re.search(r"^\s*#?\s*SECRET_KEY\s*=", texto, flags=re.MULTILINE) is None


def test_el_ejemplo_trae_la_guia_de_generacion_junto_a_la_clave():
    """RNF-07.4: un comentario justo antes de `JWT_SECRET_KEY` da la guía `openssl rand -hex 32`."""
    lineas = _leer_ejemplo().splitlines()
    posicion = next((i for i, linea in enumerate(lineas) if linea.startswith("JWT_SECRET_KEY=")), None)

    assert posicion is not None, "el ejemplo no define JWT_SECRET_KEY"
    comentarios = [linea for linea in lineas[max(0, posicion - 6):posicion] if linea.lstrip().startswith("#")]
    assert any("openssl rand -hex 32" in linea for linea in comentarios)


def test_el_ejemplo_no_trae_una_clave_de_firma_valida():
    """RNF-07.4: el valor del ejemplo nunca es una clave que la recuperación aceptaría (sería una clave real publicada)."""
    _leer_ejemplo()
    valor = dotenv_values(RUTA_DEL_EJEMPLO).get("JWT_SECRET_KEY")

    assert valor is not None
    assert cf.evaluar_clave_firma(valor).valida is False
