"""Pruebas de T4 (spec 002, RA-02.3 y RA-02.4) del marcador `infraestructura`: el ciclo de vida de la base de pruebas.

Lanzan otras corridas de `pytest` o recrean la base de la sesión, así que solo corren con
`docker compose exec backend pytest -m infraestructura` y nunca junto con las demás (plan, decisión 14b):
como la base se llama siempre `servia_pruebas`, un hijo completo la reemplaza y la elimina al terminar,
y dejaría sin base a la sesión que lo lanzó. Por eso la prueba que lanza un hijo completo cierra la base
de la sesión antes y la restaura al final.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS
from tests.soporte.proteccion import exigir_nombre_pruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
TABLA_DE_EJEMPLO = "T_Ejemplo_PRUEBA"


def _correr_pytest_hijo(*argumentos: str, timeout: int = 240):
    """Lanza `python -m pytest ...` en otro proceso, desde la raíz del backend, con el entorno actual."""
    return subprocess.run(
        [sys.executable, "-m", "pytest", *argumentos],
        cwd=RAIZ_BACKEND, env=dict(os.environ), capture_output=True, text=True, timeout=timeout,
    )


@pytest.fixture
def base_de_la_sesion_restaurada():
    """Entrega el control de la base de la sesión a la prueba y la deja creada y migrada al terminar."""
    yield
    if not entorno.base_existe(NOMBRE_PRUEBAS):
        entorno.preparar()


def test_preparar_reemplaza_una_base_de_pruebas_que_dejo_otra_corrida(base_de_la_sesion_restaurada):
    """RA-02.4: si una corrida anterior se cortó y dejó la base (aquí, con una tabla de ejemplo), `preparar()` la reemplaza."""
    from app.db.database import engine

    exigir_nombre_pruebas(engine.url.database, "la base del motor de la sesión")
    engine.dispose()
    with engine.begin() as conexion:
        conexion.execute(text(f"CREATE TABLE {TABLA_DE_EJEMPLO} (CN_Id INT)"))
    engine.dispose()
    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT OBJECT_ID(:t)"), {"t": TABLA_DE_EJEMPLO}).scalar() is not None
    engine.dispose()

    entorno.preparar()

    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT OBJECT_ID(:t)"), {"t": TABLA_DE_EJEMPLO}).scalar() is None
        assert conexion.execute(text("SELECT COUNT(*) FROM sys.tables WHERE name = 'T_Usuario'")).scalar() == 1
        assert conexion.execute(text("SELECT COUNT(*) FROM alembic_version")).scalar() == 1
    engine.dispose()


def test_un_proceso_hijo_con_solo_las_unitarias_crea_la_base_y_la_elimina_al_terminar(base_de_la_sesion_restaurada):
    """RA-02.4: toda corrida, aunque pida solo las unitarias, crea la base y la migra; al terminar, la elimina."""
    entorno.cerrar()  # el hijo usa el mismo nombre: la de la sesión se cierra antes y se restaura al final
    assert not entorno.base_existe(NOMBRE_PRUEBAS)

    hijo = _correr_pytest_hijo("-m", "unitaria", "tests/unitarias/test_marcadores.py")

    assert hijo.returncode == 0, hijo.stdout[-2000:] + hijo.stderr[-2000:]
    assert f"Base de pruebas: {NOMBRE_PRUEBAS}" in hijo.stdout  # la creó y la migró (encabezado de la corrida)
    assert "Alembic" in hijo.stdout
    assert not entorno.base_existe(NOMBRE_PRUEBAS)  # y la eliminó al terminar


def test_un_nombre_invalido_aborta_antes_de_conectarse_aunque_el_servidor_no_responda():
    """RA-02.3 (b): con un nombre que no es el de pruebas la corrida aborta con el mensaje por nombre y código distinto de cero.

    El hijo apunta SQL Server a una dirección que no responde: si abortara por «no responde» (tras 60 s),
    sería porque primero intentó conectarse. Aquí el aborto es por nombre y llega en segundos.
    """
    inicio = time.monotonic()
    hijo = _correr_pytest_hijo("-p", "tests.infraestructura.plugin_nombre_invalido", "-m", "unitaria",
                               "tests/unitarias/test_marcadores.py", timeout=120)
    duracion = time.monotonic() - inicio
    salida = hijo.stdout + hijo.stderr

    assert hijo.returncode != 0
    assert "Se aborta la suite de pruebas" in salida
    assert "debe ser exactamente 'servia_pruebas'" in salida
    assert "base_de_desarrollo_falsa" in salida
    assert "No se abrió ninguna conexión" in salida
    assert "no respondió" not in salida and "no responde" not in salida
    assert duracion < 50  # no esperó los 60 s de un servicio que no responde
