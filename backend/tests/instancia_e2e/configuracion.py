"""Configuración de la instancia de extremo a extremo (spec 005a, RA-02.41 y RNF-09.40).

Reutiliza la configuración de la suite de pytest (`tests/soporte/configuracion.py`): mismas direcciones `*.invalid`, mismos
secretos aleatorios, y solo cambia el nombre de la base y de la colección. Solo se puede construir con el nombre activo
`servia_pruebas_e2e` ya fijado por el lanzador; en una corrida de pytest aborta.
"""
import shutil
import tempfile
from pathlib import Path
from typing import Mapping

from tests.soporte import configuracion, simulados
from tests.soporte.nombres import NOMBRE_PRUEBAS_E2E
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

# Carpeta temporal de la instancia (archivos, avatares, PID, token y registro). Fuera de `/app`: una escritura ahí
# reiniciaría el servidor de desarrollo, que vigila esa carpeta.
CARPETA_E2E = Path(tempfile.gettempdir()) / "servia_e2e"

# Puerto de la instancia dentro del contenedor; `docker-compose.yml` lo publica solo en 127.0.0.1.
PUERTO_E2E = 8100

# Modo sin conexión: ni los modelos ni el rastreo de LangChain salen a internet; sin bytecode nuevo en `/app`.
VARIABLES_DE_AISLAMIENTO = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "LANGSMITH_TRACING": "false",
    "PYTHONDONTWRITEBYTECODE": "1",
}


def construir_configuracion_e2e(desarrollo: Mapping[str, str]) -> dict:
    """Arma las variables de entorno de la instancia: las de la suite, con la base y la colección `servia_pruebas_e2e`.

    Aborta si el nombre activo no es el e2e (así ninguna corrida de pytest puede armarla) y valida los dos nombres
    antes de devolver nada.
    """
    exigir_nombre_pruebas(NOMBRE_PRUEBAS_E2E, "el nombre de la instancia de extremo a extremo")
    cfg = configuracion.construir_configuracion(desarrollo)
    cfg.update({
        "SQL_SERVER_DATABASE": NOMBRE_PRUEBAS_E2E,
        "QDRANT_COLLECTION_NAME": NOMBRE_PRUEBAS_E2E,
        **VARIABLES_DE_AISLAMIENTO,
    })
    exigir_nombre_pruebas(cfg["SQL_SERVER_DATABASE"], "la base de datos (SQL_SERVER_DATABASE)")
    exigir_nombre_pruebas(cfg["QDRANT_COLLECTION_NAME"], "la colección de Qdrant (QDRANT_COLLECTION_NAME)")
    return cfg


def preparar_carpeta(carpeta: Path = CARPETA_E2E) -> Path:
    """Crea `carpeta` vacía y privada (0700) y la deja como la carpeta temporal de la sesión de los simulados.

    Reemplaza lo que dejó una corrida cortada. Se niega a trabajar dentro de la raíz del backend.
    """
    carpeta = Path(carpeta).resolve()
    if carpeta == RAIZ_BACKEND or RAIZ_BACKEND in carpeta.parents:
        raise AbortoPruebas(
            f"Se aborta la instancia de extremo a extremo: la carpeta temporal {carpeta} está dentro de {RAIZ_BACKEND}; "
            "debe estar fuera para no reiniciar el servidor de desarrollo."
        )
    shutil.rmtree(carpeta, ignore_errors=True)
    carpeta.mkdir(mode=0o700, parents=True)
    carpeta.chmod(0o700)
    simulados._estado["carpeta"] = carpeta
    return carpeta
