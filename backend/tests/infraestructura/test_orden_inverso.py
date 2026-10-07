"""Pruebas de T8 (spec 002, RA-02.7) del marcador `infraestructura`: la opción `--orden-inverso` de punta a punta.

Dos corridas hijas completas sobre las mismas pruebas (plan, decisión 14b): una en el orden normal y otra con
`--orden-inverso`. La segunda debe ejecutarlas exactamente al revés y seguir pasando, que es lo que demuestra
que ninguna depende de lo que dejó otra (RA-02.7). La lógica de la inversión (función pura) la cubren las unitarias.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
PRUEBAS = ("-m", "unitaria", "-v", "tests/unitarias/test_marcadores.py", "tests/unitarias/test_datos.py")


def _ejecutadas_en_orden(argumentos):
    """Corre un `pytest` hijo y devuelve los identificadores de las pruebas en el orden en que se ejecutaron."""
    hijo = subprocess.run(
        [sys.executable, "-m", "pytest", *argumentos],
        cwd=RAIZ_BACKEND, env=dict(os.environ), capture_output=True, text=True, timeout=300,
    )
    salida = hijo.stdout + hijo.stderr
    assert hijo.returncode == 0, salida[-3000:]
    return re.findall(r"^(tests/\S+::\S+) PASSED", salida, flags=re.MULTILINE), salida


def test_orden_inverso_ejecuta_las_mismas_pruebas_al_reves_y_todas_pasan(entorno_para_hijos):
    """RA-02.7: la corrida con `--orden-inverso` pasa y recorre exactamente al revés lo que recorre la normal."""
    normal, salida_normal = _ejecutadas_en_orden(PRUEBAS)
    inverso, salida_inversa = _ejecutadas_en_orden(("--orden-inverso", *PRUEBAS))

    assert len(normal) > 20
    assert inverso == list(reversed(normal))
    assert "Orden de las pruebas" not in salida_normal
    assert "Orden de las pruebas: inverso" in salida_inversa  # el encabezado lo dice, para no confundir una corrida con otra
    assert not entorno.base_existe(NOMBRE_PRUEBAS)
