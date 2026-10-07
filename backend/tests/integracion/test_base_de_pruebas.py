"""Pruebas de T4 (spec 002, RA-02.2, RA-02.3 y RA-02.4): la base de pruebas que crea la corrida.

Usan el SQL Server real del entorno, pero solo la base `servia_pruebas` que la propia suite creó al
inicio de la corrida y eliminará al terminar. Los módulos del sistema se importan dentro de cada
prueba (regla del plan: ningún `conftest.py` ni archivo de pruebas importa `app` al cargarse).
"""
from pathlib import Path

from sqlalchemy import text

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def _cabeza_de_alembic() -> str:
    """La revisión más reciente que declaran los archivos de migración (la que debe tener la base)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    configuracion = Config(str(RAIZ_BACKEND / "alembic.ini"))
    configuracion.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    return ScriptDirectory.from_config(configuracion).get_current_head()


def test_el_motor_de_la_corrida_apunta_a_la_base_de_pruebas():
    """RA-02.2, RA-02.3: lo que importó el sistema (valor efectivo) es la base de pruebas, no la de desarrollo."""
    from app.db.database import engine

    assert engine is not None
    assert engine.url.database == NOMBRE_PRUEBAS == "servia_pruebas"
    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT DB_NAME()")).scalar() == "servia_pruebas"


def test_la_base_de_pruebas_existe_durante_la_corrida_con_alembic_en_head():
    """RA-02.4: la base se creó al inicio y se le aplicaron las migraciones de Alembic desde cero."""
    from app.db.database import engine

    assert entorno.base_existe(NOMBRE_PRUEBAS)
    with engine.connect() as conexion:
        versiones = conexion.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
    assert versiones == [_cabeza_de_alembic()]


def test_las_migraciones_dejaron_las_tablas_y_los_catalogos_del_sistema():
    """RA-02.4: la base migrada tiene el esquema y los catálogos que siembran las migraciones (roles, estados)."""
    from app.db.database import engine

    with engine.connect() as conexion:
        tablas = set(conexion.execute(text("SELECT name FROM sys.tables")).scalars().all())
        roles = set(conexion.execute(text("SELECT CT_Nombre_rol FROM T_Rol")).scalars().all())
    assert {"T_Usuario", "T_Rol", "T_Estado", "T_Expediente", "T_Documento", "T_Bitacora", "T_Notebook"} <= tablas
    assert {"Administrador", "Usuario Judicial"} <= roles
