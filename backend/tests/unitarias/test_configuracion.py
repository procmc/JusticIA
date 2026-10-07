"""Pruebas de T2 (spec 002, RA-02.2): la suite fija su propia configuración.

Todas usan valores inventados: nunca leen `/app/.env` ni el entorno real, y no abren conexiones.
"""
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.soporte import configuracion
from tests.soporte.configuracion import (
    construir_configuracion,
    exigir_sin_modulos_importados,
    leer_configuracion_desarrollo,
)
from tests.soporte.configuracion import MODULOS_DEL_SISTEMA
from tests.soporte.proteccion import AbortoPruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

# Las seis variables que se toman de la configuración de desarrollo (RA-02.2).
LAS_SEIS = [
    "SQL_SERVER_HOST",
    "SQL_SERVER_PORT",
    "SQL_SERVER_USER",
    "SQL_SERVER_PASSWORD",
    "SQL_SERVER_DRIVER",
    "QDRANT_URL",
]

# Todas las que la suite fija por sí misma (RA-02.2), además de las seis anteriores.
LAS_FIJADAS = [
    "SQL_SERVER_DATABASE", "QDRANT_COLLECTION_NAME", "REDIS_URL",
    "JWT_SECRET_KEY",
    "ADMIN_CEDULA", "ADMIN_USERNAME", "ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_NOMBRE", "ADMIN_APELLIDO",
    "EMAIL_PROVIDER", "EMAIL_USERNAME", "EMAIL_PASSWORD", "EMAIL_HOST", "EMAIL_PORT", "EMAIL_USE_TLS",
    "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_API_KEY", "HTR_SERVER_URL",
    "ENVIRONMENT", "WHISPER_MODEL", "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE", "WHISPER_NUM_WORKERS",
    "AUDIO_CHUNK_DURATION_MIN",
    "EMBEDDING_MODEL", "DIM",
]

# Valores de desarrollo inventados (no son los reales del proyecto).
DESARROLLO_FALSO = {
    "SQL_SERVER_HOST": "servidor-falso",
    "SQL_SERVER_PORT": "14330",
    "SQL_SERVER_USER": "usuario_falso",
    "SQL_SERVER_PASSWORD": "clave-falsa-de-desarrollo",
    "SQL_SERVER_DRIVER": "Driver Falso 99",
    "QDRANT_URL": "http://qdrant-falso:6333",
}


@pytest.fixture
def cfg():
    return construir_configuracion(DESARROLLO_FALSO)


# --- (1) construir_configuracion ---------------------------------------------------------------

def test_construir_configuracion_trae_todas_las_variables_de_ra_02_2(cfg):
    """RA-02.2: están las 6 de desarrollo y las 28 que fija la suite, todas como texto."""
    assert set(cfg) == set(LAS_SEIS) | set(LAS_FIJADAS)
    assert all(isinstance(valor, str) and valor for valor in cfg.values())


def test_construir_configuracion_usa_los_valores_de_la_suite(cfg):
    """RA-02.2, RA-02.3: nombres de pruebas y direcciones que no resuelven a ningún servidor."""
    assert cfg["SQL_SERVER_DATABASE"] == "servia_pruebas"
    assert cfg["QDRANT_COLLECTION_NAME"] == "servia_pruebas"
    for clave in ("REDIS_URL", "OLLAMA_BASE_URL", "HTR_SERVER_URL"):
        assert cfg[clave].split("://", 1)[1].split(":", 1)[0].endswith(".invalid"), clave
    assert cfg["EMAIL_HOST"].endswith(".invalid")
    assert cfg["DIM"] == "1024"
    assert cfg["EMBEDDING_MODEL"] == "intfloat/multilingual-e5-large"
    # Las credenciales de administración se copian tal cual de desarrollo.
    for clave, valor in DESARROLLO_FALSO.items():
        assert cfg[clave] == valor


def test_construir_configuracion_ignora_otras_variables_de_desarrollo():
    """RA-02.2: «cualquier otra variable de desarrollo no tiene efecto sobre la suite»."""
    dev = dict(DESARROLLO_FALSO, SQL_SERVER_DATABASE="db_desarrollo", QDRANT_COLLECTION_NAME="justicia_docs",
               OLLAMA_BASE_URL="http://ollama-real:11434")
    cfg = construir_configuracion(dev)
    assert cfg["SQL_SERVER_DATABASE"] == "servia_pruebas"
    assert cfg["QDRANT_COLLECTION_NAME"] == "servia_pruebas"
    assert cfg["OLLAMA_BASE_URL"].endswith(".invalid:11434")


def test_construir_configuracion_genera_secretos_distintos_en_cada_llamada():
    """RA-02.2: JWT, contraseña del administrador sembrado y claves inventadas son aleatorias por corrida."""
    a = construir_configuracion(DESARROLLO_FALSO)
    b = construir_configuracion(DESARROLLO_FALSO)
    for clave in ("JWT_SECRET_KEY", "ADMIN_PASSWORD", "EMAIL_PASSWORD", "OLLAMA_API_KEY"):
        assert a[clave] != b[clave], clave
    assert len(a["ADMIN_PASSWORD"]) >= 8
    # Sin la contraseña por omisión de la migración consolidada.
    assert a["ADMIN_PASSWORD"] != "Admin2025!"
    assert a["ADMIN_CEDULA"] != "000000000"


def test_el_administrador_sembrado_no_lleva_el_prefijo_prueba(cfg):
    """RA-02.7: el conteo de residuos busca `PRUEBA`; el administrador de la migración no debe contarse."""
    for clave in ("ADMIN_CEDULA", "ADMIN_USERNAME", "ADMIN_EMAIL", "ADMIN_NOMBRE", "ADMIN_APELLIDO"):
        assert "PRUEBA" not in cfg[clave].upper(), clave


# --- (2) y (3) leer_configuracion_desarrollo ---------------------------------------------------

def _escribir_dotenv(ruta: Path, valores: dict) -> Path:
    ruta.write_text("\n".join(f"{k}={v}" for k, v in valores.items()) + "\n", encoding="utf-8")
    return ruta


def test_leer_configuracion_desarrollo_toma_solo_las_seis_permitidas(tmp_path):
    """RA-02.2: de `.env` y del entorno se leen únicamente las 6; las demás se ignoran."""
    dotenv = _escribir_dotenv(tmp_path / ".env", dict(
        DESARROLLO_FALSO, SQL_SERVER_DATABASE="db_desarrollo", QDRANT_COLLECTION_NAME="justicia_docs",
        JWT_SECRET_KEY="secreto-de-desarrollo"))
    leidas = leer_configuracion_desarrollo(entorno={"OLLAMA_BASE_URL": "http://real", "DIM": "768"},
                                           ruta_dotenv=dotenv)
    assert leidas == DESARROLLO_FALSO


def test_leer_configuracion_desarrollo_prefiere_el_entorno_al_dotenv(tmp_path):
    """RA-02.2: el entorno del contenedor manda; `.env` completa lo que falte."""
    dotenv = _escribir_dotenv(tmp_path / ".env", DESARROLLO_FALSO)
    leidas = leer_configuracion_desarrollo(entorno={"QDRANT_URL": "http://del-entorno:6333"}, ruta_dotenv=dotenv)
    assert leidas["QDRANT_URL"] == "http://del-entorno:6333"
    assert leidas["SQL_SERVER_HOST"] == DESARROLLO_FALSO["SQL_SERVER_HOST"]


def test_leer_configuracion_desarrollo_no_modifica_el_entorno(tmp_path):
    """Plan, decisión 5: se lee con `dotenv_values`, sin `load_dotenv` ni tocar `os.environ`."""
    import os
    antes = dict(os.environ)
    leer_configuracion_desarrollo(entorno=DESARROLLO_FALSO, ruta_dotenv=tmp_path / "no_existe.env")
    assert dict(os.environ) == antes


def test_sin_dotenv_ni_entorno_nombra_las_seis_que_faltan(tmp_path):
    """RA-02.2 (c): sin ningún `.env` aborta y nombra lo que falta."""
    with pytest.raises(AbortoPruebas) as error:
        leer_configuracion_desarrollo(entorno={}, ruta_dotenv=tmp_path / "no_existe.env")
    for nombre in LAS_SEIS:
        assert nombre in str(error.value)


@pytest.mark.parametrize("faltante", LAS_SEIS)
def test_si_falta_una_de_las_seis_aborta_con_su_nombre(faltante, tmp_path):
    """RA-02.2 (b): falta una variable de administración, aborta nombrándola y sin valor por omisión."""
    entorno = {k: v for k, v in DESARROLLO_FALSO.items() if k != faltante}
    with pytest.raises(AbortoPruebas) as error:
        leer_configuracion_desarrollo(entorno=entorno, ruta_dotenv=tmp_path / "no_existe.env")
    mensaje = str(error.value)
    assert faltante in mensaje
    # Solo nombra la que falta, y nunca muestra valores (la contraseña de SQL Server, por ejemplo).
    assert all(otra not in mensaje for otra in LAS_SEIS if otra != faltante)
    assert DESARROLLO_FALSO["SQL_SERVER_PASSWORD"] not in mensaje


def test_una_variable_vacia_cuenta_como_faltante(tmp_path):
    """RA-02.2: una variable vacía no sirve (el código usaría su valor por omisión)."""
    entorno = dict(DESARROLLO_FALSO, SQL_SERVER_HOST="")
    with pytest.raises(AbortoPruebas) as error:
        leer_configuracion_desarrollo(entorno=entorno, ruta_dotenv=tmp_path / "no_existe.env")
    assert "SQL_SERVER_HOST" in str(error.value)


# --- (4) exigir_sin_modulos_importados -----------------------------------------------------------

@pytest.mark.parametrize("modulo", ["app", "app.config.config", "main", "celery_app", "app.db.database"])
def test_un_modulo_del_sistema_ya_importado_hace_abortar(modulo):
    """RA-02.2 (a2): esos módulos ya habrían leído el entorno real."""
    with pytest.raises(AbortoPruebas) as error:
        exigir_sin_modulos_importados({"os": object(), modulo: object()})
    assert modulo in str(error.value)


def test_sin_modulos_del_sistema_no_aborta():
    """RA-02.2: nombres parecidos (`application`, `main_utils`) no son del sistema."""
    exigir_sin_modulos_importados({"os": object(), "application": object(), "main_utils": object(),
                                   "tests.soporte.configuracion": object()})


def _importaciones_al_cargar(archivo: Path):
    """Nombres de módulos que el archivo importa a nivel de módulo (no dentro de funciones)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    nombres = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            nombres += [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0:
            nombres.append(nodo.module or "")
    return nombres


def test_ningun_conftest_ni_modulo_de_soporte_importa_el_sistema_al_cargarse():
    """RA-02.2: ninguna importación a nivel de módulo trae `app`, `main` ni `celery_app` (plan, decisión 3).

    Se revisa el código (no `sys.modules`): las pruebas que importan `app` DENTRO de sus funciones,
    ya con el entorno fijado, son legítimas y dejarían ese diccionario distinto según el orden.
    """
    archivos = [RAIZ_BACKEND / "conftest.py", *sorted((RAIZ_BACKEND / "tests").rglob("conftest.py")),
                *sorted((RAIZ_BACKEND / "tests" / "soporte").glob("*.py"))]
    assert RAIZ_BACKEND / "conftest.py" in archivos and len(archivos) > 3
    for archivo in archivos:
        for nombre in _importaciones_al_cargar(archivo):
            assert nombre.split(".", 1)[0] not in MODULOS_DEL_SISTEMA, f"{archivo} importa {nombre} al cargarse"


# --- (5) proceso hijo: los `load_dotenv()` no sobrescriben lo que fijó la suite -------------------

def _arbol_con_config_y_dotenv(destino: Path, valores_dotenv: dict) -> Path:
    """Copia el `config.py` real a un árbol temporal con un `.env` de ejemplo en la raíz.

    `load_dotenv()` busca el `.env` subiendo desde el archivo que lo llama; así se reproduce el
    caso de `/app/.env` sin depender de que exista ni de su contenido.
    """
    (destino / "app" / "config").mkdir(parents=True)
    (destino / "app" / "__init__.py").write_text("", encoding="utf-8")
    (destino / "app" / "config" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy(RAIZ_BACKEND / "app" / "config" / "config.py", destino / "app" / "config" / "config.py")
    _escribir_dotenv(destino / ".env", valores_dotenv)
    return destino


_CODIGO_HIJO = """
import json, os
import app.config.config as c
claves = json.loads(os.environ["CLAVES_A_LEER"])
print(json.dumps({
    "entorno": {k: os.environ.get(k) for k in claves},
    "config": {
        "SQL_SERVER_DATABASE": c.SQL_SERVER_DATABASE, "QDRANT_COLLECTION_NAME": c.QDRANT_COLLECTION_NAME,
        "REDIS_URL": c.REDIS_URL, "OLLAMA_BASE_URL": c.OLLAMA_BASE_URL, "OLLAMA_MODEL": c.OLLAMA_MODEL,
        "HTR_SERVER_URL": c.HTR_SERVER_URL, "JWT_SECRET_KEY": c.JWT_SECRET_KEY,
        "EMBEDDING_MODEL": c.EMBEDDING_MODEL, "DIM": str(c.DIM), "WHISPER_MODEL": c.WHISPER_MODEL,
    },
}))
"""


def _correr_hijo(carpeta: Path, entorno_extra: dict) -> dict:
    entorno = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(carpeta),
               "CLAVES_A_LEER": json.dumps(LAS_SEIS + LAS_FIJADAS), **entorno_extra}
    resultado = subprocess.run([sys.executable, "-c", _CODIGO_HIJO], cwd=carpeta, env=entorno,
                               capture_output=True, text=True, timeout=60)
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def test_un_proceso_hijo_con_el_entorno_de_la_suite_no_ve_los_valores_del_dotenv(tmp_path, cfg):
    """RA-02.2 (a): los `load_dotenv()` no sobrescriben lo fijado, aunque el `.env` traiga otros valores."""
    valores_dotenv = {clave: f"valor-del-dotenv-{clave}" for clave in LAS_SEIS + LAS_FIJADAS}
    valores_dotenv["DIM"] = "384"
    carpeta = _arbol_con_config_y_dotenv(tmp_path, valores_dotenv)

    visto = _correr_hijo(carpeta, cfg)

    assert visto["entorno"] == cfg
    assert visto["config"]["SQL_SERVER_DATABASE"] == "servia_pruebas"
    assert visto["config"]["QDRANT_COLLECTION_NAME"] == "servia_pruebas"
    for clave, valor in visto["config"].items():
        assert valor == cfg[clave], clave


def test_control_sin_el_entorno_de_la_suite_el_dotenv_si_manda(tmp_path):
    """Control de la prueba anterior: sin fijar el entorno, `load_dotenv()` toma el `.env` (el riesgo real)."""
    valores_dotenv = {clave: f"valor-del-dotenv-{clave}" for clave in LAS_SEIS + LAS_FIJADAS}
    valores_dotenv["DIM"] = "384"
    carpeta = _arbol_con_config_y_dotenv(tmp_path, valores_dotenv)

    visto = _correr_hijo(carpeta, {})

    assert visto["config"]["SQL_SERVER_DATABASE"] == "valor-del-dotenv-SQL_SERVER_DATABASE"
    assert visto["config"]["QDRANT_COLLECTION_NAME"] == "valor-del-dotenv-QDRANT_COLLECTION_NAME"


def test_aplicar_fija_las_variables_en_el_entorno_indicado(cfg):
    """RA-02.2: `aplicar` deja la configuración en el entorno (en pruebas, un diccionario aparte)."""
    entorno = {"OTRA": "se conserva"}
    configuracion.aplicar(cfg, entorno)
    assert entorno["OTRA"] == "se conserva"
    assert all(entorno[clave] == valor for clave, valor in cfg.items())
