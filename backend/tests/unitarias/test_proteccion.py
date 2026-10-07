"""Pruebas de T2 (spec 002, RA-02.3): la protección del nombre de pruebas.

Ninguna abre una conexión: la fixture `sin_conexiones` hace fallar cualquier intento.
"""
import re
import socket
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.soporte import configuracion
from tests.soporte.nombres import NOMBRE_PRUEBAS
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas

URL_BASE = "mssql+pyodbc://usuario:clave%21@servidor-falso:1433/{base}?driver=Driver+Falso&TrustServerCertificate=yes"

# Nombres que deben rechazarse (valor escrito o valor efectivo).
NOMBRES_INVALIDOS = [
    pytest.param("db_ServIA", id="base-de-desarrollo"),
    pytest.param("justicia_docs", id="coleccion-de-desarrollo"),
    pytest.param("SERVIA_PRUEBAS", id="mayusculas"),
    pytest.param("Servia_Pruebas", id="mayuscula-inicial"),
    pytest.param("mi_servia_pruebas", id="lo-contiene-antes"),
    pytest.param("servia_pruebas_2", id="lo-contiene-despues"),
    pytest.param(" servia_pruebas", id="espacio-al-inicio"),
    pytest.param("servia_pruebas\n", id="salto-de-linea"),
    pytest.param("", id="vacio"),
    pytest.param("servia_pruebas; DROP DATABASE db_ServIA;--", id="inyeccion-punto-y-coma"),
    pytest.param("servia_pruebas'--", id="inyeccion-comilla"),
    pytest.param("servia_pruebas]; DROP DATABASE x; --", id="inyeccion-corchete"),
    pytest.param("master", id="master"),
    pytest.param("tempdb", id="tempdb"),
]


@pytest.fixture(autouse=True)
def sin_conexiones(monkeypatch):
    """RA-02.3: «antes de abrir ninguna conexión»; cualquier intento hace fallar la prueba."""
    def _prohibido(*args, **kwargs):
        raise AssertionError("La protección intentó abrir una conexión")

    monkeypatch.setattr(socket.socket, "connect", _prohibido)
    monkeypatch.setattr(socket, "create_connection", _prohibido)
    try:
        import pyodbc
        monkeypatch.setattr(pyodbc, "connect", _prohibido)
    except ImportError:  # pragma: no cover - pyodbc viene en la imagen del backend
        pass


def _modulo_config(base=NOMBRE_PRUEBAS, coleccion=NOMBRE_PRUEBAS, redis="redis://redis.invalid:6379",
                   ollama="http://ollama.invalid:11434", htr="http://htr.invalid:9100"):
    """Un sustituto de `app.config.config` con los valores que importaría el sistema."""
    return SimpleNamespace(DATABASE_URL=URL_BASE.format(base=base), QDRANT_COLLECTION_NAME=coleccion,
                           REDIS_URL=redis, OLLAMA_BASE_URL=ollama, HTR_SERVER_URL=htr)


ENTORNO_CORREO_INVENTADO = {"EMAIL_HOST": "smtp.correo.invalid"}


def test_el_nombre_de_pruebas_es_servia_pruebas():
    """Spec, definiciones: el nombre de la base y de la colección de pruebas."""
    assert NOMBRE_PRUEBAS == "servia_pruebas"


def test_acepta_el_nombre_exacto_sin_abrir_conexiones():
    """RA-02.3 (a): con el nombre exacto no aborta."""
    exigir_nombre_pruebas("servia_pruebas", "la base de datos")


@pytest.mark.parametrize("nombre", NOMBRES_INVALIDOS)
def test_rechaza_un_nombre_invalido_escrito(nombre):
    """RA-02.3 (a): como valor escrito, aborta con un mensaje en español que dice qué se validaba."""
    with pytest.raises(AbortoPruebas) as error:
        exigir_nombre_pruebas(nombre, "la base de datos")
    mensaje = str(error.value)
    assert "la base de datos" in mensaje
    assert NOMBRE_PRUEBAS in mensaje
    assert "servia_pruebas" in mensaje and "debe" in mensaje.lower()


@pytest.mark.parametrize("valor", [None, 0, b"servia_pruebas", ["servia_pruebas"]])
def test_rechaza_valores_que_no_son_texto(valor):
    """RA-02.3: solo vale un `str` igual al nombre de pruebas."""
    with pytest.raises(AbortoPruebas):
        exigir_nombre_pruebas(valor, "la colección")


@pytest.mark.parametrize("nombre", NOMBRES_INVALIDOS)
def test_rechaza_una_url_de_conexion_con_otra_base_como_valor_efectivo(nombre):
    """RA-02.3 (a): el valor efectivo es lo que importó `config.py`: la base que trae la URL de conexión."""
    # Los nombres con `?`, `/` o `#` cambian el análisis de la URL; también deben abortar.
    modulo = _modulo_config(base=nombre)
    with pytest.raises(AbortoPruebas):
        configuracion.validar_valores_efectivos(modulo, ENTORNO_CORREO_INVENTADO)


@pytest.mark.parametrize("nombre", NOMBRES_INVALIDOS)
def test_rechaza_un_nombre_de_coleccion_de_otro_tipo_como_valor_efectivo(nombre):
    """RA-02.3 (a): lo mismo para el nombre de la colección tal como lo usa el sistema."""
    modulo = _modulo_config(coleccion=nombre)
    with pytest.raises(AbortoPruebas) as error:
        configuracion.validar_valores_efectivos(modulo, ENTORNO_CORREO_INVENTADO)
    assert "colecci" in str(error.value).lower()


def test_acepta_los_valores_efectivos_de_la_suite():
    """RA-02.3: la configuración efectiva correcta no aborta."""
    configuracion.validar_valores_efectivos(_modulo_config(), ENTORNO_CORREO_INVENTADO)


@pytest.mark.parametrize(
    "cambio, nombre_variable",
    [
        ({"redis": "redis://redis:6379"}, "REDIS_URL"),
        ({"ollama": "http://ollama:11434"}, "OLLAMA_BASE_URL"),
        ({"htr": "http://servidor-htr:9100"}, "HTR_SERVER_URL"),
    ],
)
def test_rechaza_direcciones_que_resuelven_a_un_servicio_real(cambio, nombre_variable):
    """RA-02.2, RA-02.3: Redis, Ollama y HTR deben apuntar a `*.invalid` en el valor efectivo."""
    with pytest.raises(AbortoPruebas) as error:
        configuracion.validar_valores_efectivos(_modulo_config(**cambio), ENTORNO_CORREO_INVENTADO)
    assert nombre_variable in str(error.value)


def test_rechaza_un_servidor_de_correo_real():
    """RA-02.2: el servidor de correo efectivo también debe ser `*.invalid`."""
    with pytest.raises(AbortoPruebas) as error:
        configuracion.validar_valores_efectivos(_modulo_config(), {"EMAIL_HOST": "sandbox.smtp.mailtrap.io"})
    assert "EMAIL_HOST" in str(error.value)


def test_la_url_con_la_base_de_pruebas_pasa_aunque_la_clave_tenga_simbolos():
    """RA-02.3: el análisis de la URL no se confunde con contraseñas con símbolos."""
    modulo = _modulo_config()
    modulo.DATABASE_URL = "mssql+pyodbc://sa:p%40ss%2Fw%3Frd%23@servidor:1433/servia_pruebas?driver=D&TrustServerCertificate=yes"
    configuracion.validar_valores_efectivos(modulo, ENTORNO_CORREO_INVENTADO)


# --- O1: el DDL de Qdrant solo sale de `proteccion.py` (prueba estática) ---------------------------------

RAIZ_TESTS = Path(__file__).resolve().parents[1]
LLAMADAS_DE_DDL_DE_QDRANT = re.compile(r"\b(?:create_collection|delete_collection|recreate_collection)\b")
# Fuera de `proteccion.py` solo las pueden nombrar los dobles de prueba (un cliente falso que registra llamadas).
PERMITIDOS_PARA_DDL_DE_QDRANT = {"soporte/proteccion.py", "unitarias/test_coleccion_de_pruebas.py", "unitarias/test_proteccion.py"}


def _archivos_que_nombran_el_ddl_de_qdrant(raiz: Path):
    return sorted(
        archivo.relative_to(raiz).as_posix()
        for archivo in raiz.rglob("*.py")
        if "__pycache__" not in archivo.parts and LLAMADAS_DE_DDL_DE_QDRANT.search(archivo.read_text(encoding="utf-8"))
    )


def test_o1_crear_o_eliminar_colecciones_solo_se_hace_desde_proteccion():
    """RA-02.3 (O1): nada en `backend/tests/` crea o elimina colecciones de Qdrant sin pasar por la validación del nombre."""
    fuera_de_lugar = [a for a in _archivos_que_nombran_el_ddl_de_qdrant(RAIZ_TESTS) if a not in PERMITIDOS_PARA_DDL_DE_QDRANT]
    assert fuera_de_lugar == [], f"Estos archivos llaman al DDL de Qdrant sin pasar por proteccion.py: {fuera_de_lugar}"
    assert "soporte/proteccion.py" in _archivos_que_nombran_el_ddl_de_qdrant(RAIZ_TESTS)  # la búsqueda sí encuentra el punto protegido


def test_o1_la_busqueda_detecta_una_llamada_suelta(tmp_path):
    """La prueba estática no es decorativa: encuentra la llamada en un archivo ajeno."""
    (tmp_path / "test_ajeno.py").write_text("cliente.recreate_collection('justicia_docs')\n", encoding="utf-8")
    (tmp_path / "test_limpio.py").write_text("assert True\n", encoding="utf-8")
    assert _archivos_que_nombran_el_ddl_de_qdrant(tmp_path) == ["test_ajeno.py"]
