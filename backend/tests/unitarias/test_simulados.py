"""Pruebas de T6 (spec 002, RA-02.5): Redis simulado, Celery inmediato y carpeta temporal de archivos.

Los módulos del sistema se importan DENTRO de cada prueba (nunca al cargar este archivo): el
`conftest.py` ya fijó la configuración de la suite y simuló Redis antes de que se importe `app`.
Ninguna usa SQL Server, Qdrant ni el Redis real.
"""
import os
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import fakeredis
import pytest
import redis
from celery import Celery

from tests.soporte import simulados

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
UPLOADS_REAL = RAIZ_BACKEND / "uploads"


def _es_de_desarrollo(ruta) -> bool:
    """¿Está la ruta dentro de la raíz del backend (donde vive el `uploads/` real)?"""
    ruta = Path(ruta).resolve()
    return ruta == RAIZ_BACKEND or RAIZ_BACKEND in ruta.parents


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier conexión de red hace fallar la prueba (el Redis real no debe tocarse)."""
    def _prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", _prohibido)
    monkeypatch.setattr(socket, "create_connection", _prohibido)


# --- Redis simulado ------------------------------------------------------------------------------

def test_redis_redis_es_el_simulado(sin_red):
    """RA-02.5: `redis.Redis` y `redis.Redis.from_url` son el simulado (sin conexión de red)."""
    assert issubclass(redis.Redis, fakeredis.FakeRedis)
    cliente = redis.Redis(host="cualquiera.invalid", port=6379, db=2, decode_responses=True, socket_timeout=5)
    assert isinstance(cliente, fakeredis.FakeRedis)
    assert cliente.ping() is True

    desde_url = redis.Redis.from_url("redis://otro.invalid:6379", decode_responses=True)
    assert isinstance(desde_url, fakeredis.FakeRedis)
    assert desde_url.ping() is True


def test_los_clientes_simulados_comparten_el_mismo_servidor(sin_red):
    """RA-02.5: como en el Redis real, lo que escribe un cliente lo lee otro (las conversaciones y el
    progreso de ingesta usan clientes distintos)."""
    a = redis.Redis.from_url("redis://uno.invalid:6379/2", decode_responses=True)
    b = redis.Redis(host="dos.invalid", port=6379, db=2, decode_responses=True)
    a.set("PRUEBA:clave", "valor")
    assert b.get("PRUEBA:clave") == "valor"
    a.zadd("PRUEBA:z", {"m": 1})
    assert b.zrevrange("PRUEBA:z", 0, -1) == ["m"]
    # Cada base numerada es independiente, igual que en Redis.
    assert redis.Redis.from_url("redis://uno.invalid:6379/0").get("PRUEBA:clave") is None
    a.delete("PRUEBA:clave", "PRUEBA:z")


def test_el_redis_simulado_responde_info_de_memoria(sin_red):
    """El sistema pide `INFO memory` (estadísticas de conversaciones); fakeredis no lo implementa."""
    cliente = redis.Redis.from_url("redis://uno.invalid:6379/2", decode_responses=True)
    assert cliente.info("memory")["used_memory"] == 0


def test_instalar_redis_simulado_es_idempotente():
    """No se envuelve dos veces: el servidor y la clase siguen siendo los mismos."""
    clase = redis.Redis
    servidor = simulados.instalar_redis_simulado()
    assert redis.Redis is clase
    assert simulados.instalar_redis_simulado() is servidor


def test_redis_url_apunta_a_una_direccion_que_no_resuelve():
    """RA-02.5: la suite fijó `REDIS_URL` con un host `.invalid`: nunca llega al Redis real."""
    host = urlparse(os.environ["REDIS_URL"]).hostname
    assert host.endswith(".invalid")
    with pytest.raises(socket.gaierror):
        socket.getaddrinfo(host, 6379)


def test_conversation_store_se_crea_sin_redis_real(sin_red):
    """RA-02.5: `ConversationStore()` hace `ping()` al crearse; con el simulado no hay conexión de red."""
    from app.services.RAG.session_store import ConversationStore

    almacen = ConversationStore()
    assert isinstance(almacen._redis_history.redis_client, fakeredis.FakeRedis)


def test_el_progreso_de_ingesta_usa_el_cliente_simulado():
    """RA-02.5: `progress_tracker` crea su cliente al importarse; es el simulado."""
    from app.services.ingesta.async_processing import progress_tracker

    assert isinstance(progress_tracker.redis_client, fakeredis.FakeRedis)


# --- Celery inmediato ----------------------------------------------------------------------------

@pytest.fixture
def aplicacion_celery_ajena():
    """Una aplicación Celery propia de la prueba, con un broker «real» que no debe usarse."""
    aplicacion = Celery("prueba_suite", broker="redis://broker-real.invalid:6379/0",
                        backend="redis://broker-real.invalid:6379/1")

    @aplicacion.task(name="prueba_suite.sumar")
    def sumar(a, b):
        return a + b

    aplicacion.sumar = sumar
    return aplicacion


def test_fijar_celery_inmediato_configura_la_aplicacion(aplicacion_celery_ajena):
    """RA-02.5: ejecución inmediata, sin publicar en ninguna cola y con resultados en memoria."""
    anteriores = simulados.fijar_celery_inmediato(aplicacion_celery_ajena)
    conf = aplicacion_celery_ajena.conf
    assert conf.task_always_eager is True
    assert conf.task_eager_propagates is True
    assert conf.broker_url == "memory://"
    assert conf.result_backend == "cache+memory://"
    assert anteriores["broker_url"] == "redis://broker-real.invalid:6379/0"


def test_una_tarea_se_ejecuta_dentro_del_proceso_sin_tocar_ningun_broker(aplicacion_celery_ajena, sin_red):
    """RA-02.5: `.delay()` corre en el proceso (el worker real nunca la consume) y no abre conexiones."""
    simulados.fijar_celery_inmediato(aplicacion_celery_ajena)
    resultado = aplicacion_celery_ajena.sumar.delay(2, 3)
    assert resultado.get() == 5


def test_restaurar_celery_devuelve_la_configuracion_anterior(aplicacion_celery_ajena):
    """La fixture deja la aplicación como estaba al terminar cada prueba."""
    anteriores = simulados.fijar_celery_inmediato(aplicacion_celery_ajena)
    simulados.restaurar_celery(aplicacion_celery_ajena, anteriores)
    conf = aplicacion_celery_ajena.conf
    assert conf.task_always_eager is False
    assert conf.broker_url == "redis://broker-real.invalid:6379/0"


@pytest.fixture
def aplicacion_celery(aplicacion_celery_ajena):
    """Sustituye a la aplicación real de `celery_app` solo en esta prueba de la propia fixture."""
    return aplicacion_celery_ajena


def test_la_fixture_celery_inmediato_aplica_y_restaura(aplicacion_celery, celery_inmediato, sin_red):
    """RA-02.5: la fixture `celery_inmediato` deja la aplicación en modo inmediato durante la prueba."""
    assert aplicacion_celery.conf.task_always_eager is True
    assert aplicacion_celery.sumar.delay(1, 1).get() == 2


# --- Carpeta temporal de archivos ----------------------------------------------------------------

def test_la_carpeta_de_la_sesion_esta_en_tmp_y_se_elimina():
    """RA-02.5: carpeta temporal propia, fuera de `/app` (así no dispara el `--reload`), eliminada al terminar."""
    carpeta = simulados.carpeta_temporal_de_la_sesion()
    try:
        assert carpeta.is_dir()
        assert carpeta.parent == Path(tempfile.gettempdir())
        assert carpeta.name.startswith("servia_pruebas_")
        assert not _es_de_desarrollo(carpeta)
        assert simulados.carpeta_temporal_de_la_sesion() == carpeta  # una sola por sesión
    finally:
        simulados.eliminar_carpeta_temporal()
    assert not carpeta.exists()


def test_desviar_carpetas_cambia_y_restaura_las_rutas_de_uploads():
    """RA-02.5: `BASE_UPLOAD_DIR` y `upload_dir` apuntan a la carpeta temporal y luego se restauran."""
    from app.services.avatar_service import avatar_service
    from app.services.documentos.file_management_service import file_management_service

    uploads_antes = sorted(p.name for p in UPLOADS_REAL.iterdir())
    base_antes, avatares_antes = file_management_service.BASE_UPLOAD_DIR, avatar_service.upload_dir
    assert Path(base_antes) == UPLOADS_REAL  # el valor real de desarrollo

    with simulados.desviar_carpetas() as carpeta:
        assert not _es_de_desarrollo(carpeta)
        assert Path(file_management_service.BASE_UPLOAD_DIR).parent == carpeta
        assert Path(avatar_service.upload_dir).parent == carpeta
        assert not _es_de_desarrollo(file_management_service.BASE_UPLOAD_DIR)
        assert not _es_de_desarrollo(avatar_service.upload_dir)
        assert Path(file_management_service.BASE_UPLOAD_DIR).is_dir()
        assert Path(avatar_service.upload_dir).is_dir()

    assert file_management_service.BASE_UPLOAD_DIR == base_antes
    assert avatar_service.upload_dir == avatares_antes
    assert not carpeta.exists()  # la subcarpeta de la prueba se elimina al terminar
    assert sorted(p.name for p in UPLOADS_REAL.iterdir()) == uploads_antes


def test_la_fixture_carpeta_archivos_desvia_las_rutas(carpeta_archivos):
    """RA-02.5: la fixture entrega la carpeta y deja las dos rutas apuntando a ella."""
    from app.services.avatar_service import avatar_service
    from app.services.documentos.file_management_service import file_management_service

    assert not _es_de_desarrollo(carpeta_archivos)
    assert Path(file_management_service.BASE_UPLOAD_DIR).parent == carpeta_archivos
    assert Path(avatar_service.upload_dir).parent == carpeta_archivos
