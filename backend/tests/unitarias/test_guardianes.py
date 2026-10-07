"""Pruebas de T7 (spec 002, RA-02.6): los guardianes de las pruebas unitarias.

Una prueba unitaria no puede usar SQL Server, Qdrant, Tika ni el modelo de embeddings reales: el
guardián (fixture automática de `tests/unitarias/conftest.py`) hace fallar la prueba y deja el
modelo de embeddings en un falso de tamaño `DIM`. Los servicios reales se prueban en integración.
"""
import asyncio
import importlib
import os
import sys
import textwrap

import pytest

from tests.soporte import simulados
from tests.soporte.simulados import ServicioRealProhibido


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier conexión de red hace fallar la prueba: el guardián debe frenar antes de llegar a ella."""
    import socket

    def _prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", _prohibido)
    monkeypatch.setattr(socket, "create_connection", _prohibido)


# --- Qdrant --------------------------------------------------------------------------------------

def test_el_guardian_hace_fallar_una_prueba_que_intenta_usar_qdrant_real(guardian_servicios, sin_red):
    """RA-02.6: crear un cliente de Qdrant en una unitaria falla nombrando el servicio, sin conexión."""
    from qdrant_client import QdrantClient

    with pytest.raises(ServicioRealProhibido, match="Qdrant"):
        QdrantClient(url="http://qdrant-simulado.invalid:6333")
    assert guardian_servicios.intentos == ["Qdrant"]
    guardian_servicios.reconocer()  # esta prueba esperaba el intento: el cierre no la hace fallar


def test_el_guardian_tambien_frena_el_cliente_asincrono_de_qdrant(guardian_servicios, sin_red):
    from qdrant_client import AsyncQdrantClient

    with pytest.raises(ServicioRealProhibido, match="Qdrant"):
        AsyncQdrantClient(url="http://qdrant-simulado.invalid:6333")
    guardian_servicios.reconocer()


def test_un_error_atrapado_por_el_codigo_igual_queda_registrado(guardian_servicios, sin_red):
    """El código del sistema suele atrapar `Exception`: el intento queda en el registro del guardián."""
    from qdrant_client import QdrantClient

    try:
        QdrantClient(url="http://qdrant-simulado.invalid:6333")
    except Exception:
        pass
    assert guardian_servicios.intentos == ["Qdrant"]
    with pytest.raises(pytest.fail.Exception, match="Qdrant"):
        guardian_servicios.exigir_sin_intentos()  # esto es lo que haría fallar la prueba al cerrar
    guardian_servicios.reconocer()


def test_reconocer_un_servicio_solo_quita_ese_intento(guardian_servicios):
    guardian_servicios.registrar("Qdrant")
    guardian_servicios.registrar("Tika")
    guardian_servicios.reconocer("Qdrant")
    assert guardian_servicios.intentos == ["Tika"]
    guardian_servicios.reconocer()
    assert guardian_servicios.intentos == []
    guardian_servicios.exigir_sin_intentos()


# --- SQL Server ----------------------------------------------------------------------------------

def test_importar_la_base_de_datos_real_en_una_unitaria_falla_sin_conectarse(guardian_servicios, sin_red, monkeypatch):
    """`database.py` se conecta a SQL Server al importarse (10 intentos): el guardián lo impide.

    Solo cubre una importación NUEVA (se quita el módulo de `sys.modules`). Desde T4 toda corrida lo
    importa al inicio, así que la situación real es la de las pruebas de O1, más abajo.
    """
    monkeypatch.delitem(sys.modules, "app.db.database", raising=False)  # por si otra prueba lo hubiera cargado
    with pytest.raises(ServicioRealProhibido, match="SQL Server"):
        importlib.import_module("app.db.database")
    assert "app.db.database" not in sys.modules
    guardian_servicios.reconocer()


# --- O1: con la base de pruebas ya importada (plan, §12) --------------------------------------------

def test_o1_precondicion_toda_corrida_ya_importo_la_base_de_datos_de_pruebas():
    """O1: desde T4 el módulo que se conecta a la base se importa al inicio de TODA corrida, ya contra la de pruebas.

    Es la precondición de las pruebas siguientes: si dejara de cumplirse, el bloqueo por importación
    volvería a funcionar y estas pruebas ya no representarían la situación real.
    """
    assert "app.db.database" in sys.modules
    motor = sys.modules["app.db.database"].engine
    assert motor is not None
    assert motor.url.database == "servia_pruebas"


def test_o1_con_la_base_ya_importada_pyodbc_connect_sigue_bloqueado(guardian_servicios, sin_red):
    """O1: sin importación que bloquear, el conector de SQL Server sigue frenado por el guardián."""
    import pyodbc

    assert "app.db.database" in sys.modules  # precondición
    with pytest.raises(ServicioRealProhibido, match="SQL Server"):
        pyodbc.connect("DRIVER={x};SERVER=sqlserver-simulado.invalid")
    assert guardian_servicios.intentos == ["SQL Server"]
    guardian_servicios.reconocer()


def test_o1_el_motor_ya_creado_no_abre_conexiones_desde_una_unitaria(guardian_servicios, sin_red):
    """O1: `engine.connect()` del motor ya creado lanza `ServicioRealProhibido` nombrando SQL Server,
    sin abrir ninguna conexión (ni siquiera reutiliza una que otra prueba haya dejado en el pool)."""
    assert "app.db.database" in sys.modules  # precondición
    motor = sys.modules["app.db.database"].engine

    with pytest.raises(ServicioRealProhibido, match="SQL Server"):
        motor.connect()

    assert motor.pool.checkedout() == 0
    assert motor.pool.checkedin() == 0  # el pool sigue vacío: no se abrió ninguna conexión
    assert guardian_servicios.intentos == ["SQL Server"]
    guardian_servicios.reconocer()


def test_o1_el_guardian_vacia_el_pool_para_que_una_conexion_vieja_no_lo_esquive(guardian_servicios, monkeypatch):
    """O1: las pruebas de integración corren antes y dejan conexiones reales en el pool del motor; sin vaciarlo,
    `engine.connect()` las reutilizaría y una unitaria usaría SQL Server de verdad sin que el guardián se entere."""
    class MotorFalso:
        vaciado = 0

        def dispose(self):
            MotorFalso.vaciado += 1

    class ModuloFalso:
        engine = MotorFalso()

    guardian_servicios.desinstalar()
    monkeypatch.setitem(sys.modules, "app.db.database", ModuloFalso)
    otro = simulados.GuardianServicios()
    try:
        otro.instalar()
    finally:
        otro.desinstalar()
    assert MotorFalso.vaciado == 1


def test_el_conector_de_sql_server_esta_bloqueado(guardian_servicios, sin_red):
    import pyodbc

    with pytest.raises(ServicioRealProhibido, match="SQL Server"):
        pyodbc.connect("DRIVER={x};SERVER=sqlserver-simulado.invalid")
    guardian_servicios.reconocer()


# --- M1: el cliente de Qdrant que una prueba de integración dejó en caché ---------------------------

class _ClienteEnCache:
    """Hace de cliente de Qdrant (o de vectorstore) que una prueba de integración anterior dejó creado.

    No es un `QdrantClient` de verdad (una unitaria no puede crearlo), pero se comporta como uno que ya
    existe: responde sin abrir ningún guardián, que es justo el hueco que el guardián debe cerrar.
    """

    def __init__(self):
        self.llamadas = []

    def get_collection(self, *args, **kwargs):
        self.llamadas.append("get_collection")
        return type("Info", (), {"points_count": 0})()

    def add_documents(self, *args, **kwargs):
        self.llamadas.append("add_documents")
        return []


@pytest.mark.parametrize(
    "singleton, operacion",
    [
        pytest.param("_qdrant_client", "get_stats", id="cliente-en-cache"),
        pytest.param("_langchain_vectorstore", "add_documents", id="vectorstore-en-cache"),
    ],
)
def test_m1_un_cliente_de_qdrant_en_cache_no_esquiva_al_guardian(guardian_servicios, monkeypatch, singleton, operacion):
    """RA-02.6, RA-02.7 (M1): `get_vectorstore_backend()` reutiliza los singletons del módulo. Si una prueba de
    integración los dejó creados con un cliente real, el guardián de la unitaria debe frenarlos igual: si no, la
    unitaria pasaría en la suite completa (usando Qdrant real) y fallaría sola con `-m unitaria`.

    No depende del orden de la corrida: la prueba deja el caché puesto ANTES de instalar un guardián nuevo,
    como lo dejaría la integración antes de que empiece una unitaria.
    """
    from app.vectorstore import get_vectorstore_backend, qdrant_backend

    guardian_servicios.desinstalar()
    en_cache = _ClienteEnCache()
    monkeypatch.setattr(qdrant_backend, singleton, en_cache)
    guardian = simulados.GuardianServicios()
    guardian.instalar()
    try:
        argumentos = [[]] if operacion == "add_documents" else []
        with pytest.raises(ServicioRealProhibido, match="Qdrant"):
            asyncio.run(getattr(get_vectorstore_backend(), operacion)(*argumentos))
        assert en_cache.llamadas == []  # no llegó a usar el cliente que estaba en caché
        assert guardian.intentos == ["Qdrant"]
        guardian.reconocer()
    finally:
        guardian.desinstalar()

    assert getattr(qdrant_backend, singleton) is en_cache  # y al terminar vuelve el que había: no se pierde el de la integración


# --- Tika ----------------------------------------------------------------------------------------

def test_el_guardian_frena_a_tika(guardian_servicios, sin_red):
    from app.services.ingesta.tika_service import tika_service

    with pytest.raises(ServicioRealProhibido, match="Tika"):
        tika_service.extract_text(b"contenido inventado", "prueba.pdf")
    with pytest.raises(ServicioRealProhibido, match="Tika"):
        tika_service.is_available()
    assert guardian_servicios.intentos == ["Tika", "Tika"]
    guardian_servicios.reconocer()


# --- Modelo de embeddings ------------------------------------------------------------------------

def test_los_embeddings_son_un_falso_de_tamano_dim(guardian_servicios):
    """RA-02.6: sin cargar el modelo real, las consultas y los documentos dan vectores de `DIM` dimensiones."""
    from app.embeddings.embeddings import get_embeddings

    dim = int(os.environ["DIM"])
    embeddings = asyncio.run(get_embeddings())

    consulta = asyncio.run(embeddings.aembed_query("¿Qué dice el tema PRUEBA?"))
    documentos = asyncio.run(embeddings.aembed_documents(["fragmento uno PRUEBA", "fragmento dos PRUEBA"]))

    assert len(consulta) == dim
    assert [len(v) for v in documentos] == [dim, dim]
    assert all(isinstance(x, float) for x in consulta)
    assert documentos[0] != documentos[1]  # textos distintos, vectores distintos
    assert asyncio.run(embeddings.aembed_query("¿Qué dice el tema PRUEBA?")) == consulta  # y es determinista


def test_el_falso_de_embeddings_conserva_los_prefijos_e5_del_sistema(guardian_servicios):
    """Lo que se simula es el modelo, no `EmbeddingsWrapper`: su lógica de prefijos sigue siendo la real."""
    from app.embeddings.embeddings import get_embeddings

    embeddings = asyncio.run(get_embeddings())
    asyncio.run(embeddings.aembed_query("hola PRUEBA"))
    asyncio.run(embeddings.aembed_documents(["adiós PRUEBA"]))

    assert embeddings.model.textos == ["query: hola PRUEBA", "passage: adiós PRUEBA"]


def test_cargar_el_modelo_real_de_embeddings_en_una_unitaria_falla(guardian_servicios, sin_red):
    from app.embeddings import embeddings as modulo

    with pytest.raises(ServicioRealProhibido, match="embeddings"):
        modulo.SentenceTransformer("intfloat/multilingual-e5-large")
    guardian_servicios.reconocer()


# --- Cómo se instalan y se quitan ----------------------------------------------------------------

def test_al_desinstalar_se_restauran_las_clases_reales(guardian_servicios, monkeypatch):
    """O4: lo que había antes de instalar el guardián (aquí, un valor reconocible) vuelve EXACTAMENTE al desinstalarlo."""
    from qdrant_client import QdrantClient
    from app.embeddings import embeddings as modulo

    guardian_servicios.desinstalar()  # esta prueba instala el suyo, sobre un estado que ella controla
    original_init = QdrantClient.__init__
    original_modelo = modulo.SentenceTransformer
    original = object()  # lo que dejó una corrida anterior (sin cargar, o el modelo real de la integración)
    monkeypatch.setattr(modulo, "_embeddings", original)

    otro = simulados.GuardianServicios()
    otro.instalar()
    try:
        assert QdrantClient.__init__ is not original_init
        assert modulo._embeddings is not original
        assert isinstance(modulo._embeddings.model, simulados.ModeloEmbeddingsFalso)
    finally:
        otro.desinstalar()

    assert QdrantClient.__init__ is original_init
    assert modulo.SentenceTransformer is original_modelo
    assert modulo._embeddings is original  # exactamente el valor que había, no «uno que no es el falso»
    otro.desinstalar()  # idempotente


def test_el_buscador_parchea_un_modulo_despues_de_importarlo(tmp_path, monkeypatch):
    """Los módulos pesados (Qdrant, embeddings) solo se importan si una prueba los pide, y quedan parchados."""
    (tmp_path / "modulo_guardian_de_prueba.py").write_text(textwrap.dedent("""
        SERVICIO = "real"
    """), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, "modulo_guardian_de_prueba", raising=False)

    buscador = simulados.BuscadorGuardian(
        parches={"modulo_guardian_de_prueba": lambda modulo: setattr(modulo, "SERVICIO", "parchado")},
        bloqueados={},
    )
    sys.meta_path.insert(0, buscador)
    try:
        modulo = importlib.import_module("modulo_guardian_de_prueba")
    finally:
        sys.meta_path.remove(buscador)
        sys.modules.pop("modulo_guardian_de_prueba", None)
    assert modulo.SERVICIO == "parchado"


def test_el_buscador_bloquea_un_modulo_antes_de_ejecutarlo(tmp_path, monkeypatch):
    (tmp_path / "modulo_bloqueado_de_prueba.py").write_text("raise RuntimeError('se ejecutó')\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))

    def _prohibido():
        raise ServicioRealProhibido("Servicio de prueba")

    buscador = simulados.BuscadorGuardian(parches={}, bloqueados={"modulo_bloqueado_de_prueba": _prohibido})
    sys.meta_path.insert(0, buscador)
    try:
        with pytest.raises(ServicioRealProhibido, match="Servicio de prueba"):
            importlib.import_module("modulo_bloqueado_de_prueba")
    finally:
        sys.meta_path.remove(buscador)


# --- (d) de RA-02.6: un error atrapado igual hace fallar la prueba al cerrarse, nombrando el servicio -----------

def _intento_de_qdrant():
    from qdrant_client import QdrantClient

    QdrantClient(url="http://qdrant-simulado.invalid:6333")


def _intento_de_sql_server():
    import pyodbc

    pyodbc.connect("DRIVER={x};SERVER=sqlserver-simulado.invalid")


def _intento_de_tika():
    from app.services.ingesta.tika_service import tika_service

    tika_service.is_available()


@pytest.mark.parametrize(
    "servicio, intento",
    [
        pytest.param("Qdrant", _intento_de_qdrant, id="qdrant"),
        pytest.param("SQL Server", _intento_de_sql_server, id="sql-server"),
        pytest.param("Tika", _intento_de_tika, id="tika"),
    ],
)
def test_d_un_intento_registrado_de_cada_servicio_hace_fallar_el_cierre_nombrandolo(
    guardian_servicios, sin_red, servicio, intento
):
    """RA-02.6 (d), parte unitaria (plan, decisión 10b): el código del sistema atrapa `Exception`, pero el intento
    queda registrado y `exigir_sin_intentos()` (lo que ejecuta la fixture al cerrarse) lanza nombrando ESE servicio.

    El camino de principio a fin (que la fixture real lo ejecute al cerrar la prueba) lo comprueba una corrida
    hija del marcador `infraestructura`.
    """
    try:
        intento()
    except Exception:  # como lo haría el código del sistema: la prueba «pasaría» sin el guardián
        pass

    assert guardian_servicios.intentos == [servicio]
    with pytest.raises(pytest.fail.Exception) as error:
        guardian_servicios.exigir_sin_intentos()
    mensaje = str(error.value)
    assert servicio in mensaje
    assert "servicios reales" in mensaje
    for otro in {"Qdrant", "SQL Server", "Tika"} - {servicio}:
        assert otro not in mensaje
    guardian_servicios.reconocer()  # esta prueba esperaba el intento: su propio cierre no falla


def test_d_varios_intentos_se_nombran_todos_sin_repetir(guardian_servicios):
    guardian_servicios.registrar("Qdrant")
    guardian_servicios.registrar("Tika")
    guardian_servicios.registrar("Qdrant")
    with pytest.raises(pytest.fail.Exception) as error:
        guardian_servicios.exigir_sin_intentos()
    assert str(error.value).count("Qdrant") == 1 and "Tika" in str(error.value)
    guardian_servicios.reconocer()
