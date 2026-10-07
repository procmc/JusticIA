"""Pruebas de T6 (spec 002, RA-02.5): una tarea real del sistema, disparada con `.delay()`, corre dentro de la prueba.

Se usa `procesar_archivo_celery`, la tarea de ingesta. Con Redis simulado y Celery inmediato no hay worker, ni
broker ni Redis real: la tarea se ejecuta en este proceso y su resultado se observa aquí mismo. NO se guarda
ningún archivo (el guardado real fuera de `/app` es de la futura spec de ingesta, decisión 7 del plan) y ningún
servicio real participa: los datos son inventados (prefijo `PRUEBA`) y la prueba corta cualquier conexión de red
de Python, de modo que un Redis real, o un broker, harían fallar la prueba. Las dos piden `carpeta_archivos` como defensa:
si algún día la tarea llegara a guardar un archivo, caería en la carpeta temporal y nunca en el `uploads/` real.
"""
import json
import socket

import pytest

# `check_if_cancelled` de la tarea consulta el estado en Celery; en modo inmediato Celery avisa que ese resultado
# no se guarda en el backend. Es un aviso del propio sistema en un modo que nunca usa en producción.
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

TEMA = "PRUEBA-TEMA-CELERY"
ARCHIVO = "PRUEBA_celery_inventado.txt"
USUARIO = "PRUEBA"


@pytest.fixture
def sin_red(monkeypatch):
    """Cualquier conexión de red de Python hace fallar la prueba (SQL Server usa `pyodbc`, que no pasa por aquí)."""
    def _prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", _prohibido)
    monkeypatch.setattr(socket, "create_connection", _prohibido)


@pytest.fixture
def redis_del_progreso():
    """El cliente de Redis del seguimiento de progreso del sistema; al terminar borra las claves de la prueba."""
    from app.services.ingesta.async_processing import progress_tracker

    antes = set(progress_tracker.redis_client.keys("task_progress:*"))
    yield progress_tracker.redis_client
    for clave in set(progress_tracker.redis_client.keys("task_progress:*")) - antes:
        progress_tracker.redis_client.delete(clave)


def test_delay_ejecuta_la_tarea_de_ingesta_en_el_proceso_y_lee_el_redis_simulado(
    celery_inmediato, redis_del_progreso, sin_red, carpeta_archivos
):
    """RA-02.5: `.delay()` corre la tarea real en este proceso y su resultado sale de lo que hay en el Redis simulado.

    Se deja en el Redis simulado el seguimiento de una tarea ya completada; la tarea real lo encuentra (su
    verificación de idempotencia) y devuelve el resultado previo sin procesar nada. Que lo encuentre prueba que
    el cliente de Redis que usó el código del sistema es el simulado; que no haya red, que no hay broker real.
    """
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    id_tarea = "PRUEBA-tarea-completada-antes"
    progress_manager.create_tracker(id_tarea).mark_completed("PRUEBA: terminada antes")

    # `signature(...).set(task_id=...).delay()` fija el identificador para poder preparar el Redis simulado.
    resultado = procesar_archivo_celery.signature((TEMA, {"filename": ARCHIVO}, USUARIO)).set(task_id=id_tarea).delay()

    assert celery_inmediato.conf.task_always_eager is True
    assert resultado.id == id_tarea
    assert resultado.successful()
    respuesta = resultado.get()
    assert respuesta["status"] == "completado"
    assert respuesta["resultado"]["filename"] == ARCHIVO
    assert "reintento evitado" in respuesta["note"]


def test_delay_deja_el_estado_de_la_tarea_en_el_redis_simulado_y_propaga_su_error(
    celery_inmediato, redis_del_progreso, sin_red, carpeta_archivos
):
    """RA-02.5: con `.delay()` directo, la tarea real crea su seguimiento en el Redis simulado y su error llega a la prueba.

    Los datos están incompletos a propósito (sin el contenido del archivo), así la tarea falla antes de guardar o
    procesar nada. El modo inmediato propaga la excepción a quien llama (`task_eager_propagates`) y el estado
    «fallido» queda en el Redis simulado, donde lo lee el endpoint de progreso del sistema.
    """
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

    claves_antes = set(redis_del_progreso.keys("task_progress:*"))

    with pytest.raises(KeyError, match="content"):
        procesar_archivo_celery.delay(TEMA, {"filename": ARCHIVO}, USUARIO)

    nuevas = set(redis_del_progreso.keys("task_progress:*")) - claves_antes
    assert len(nuevas) == 1, "la tarea debía crear exactamente un seguimiento en el Redis simulado"
    estado = json.loads(redis_del_progreso.get(nuevas.pop()))
    assert estado["status"] == "fallido"
    assert ARCHIVO in estado["message"]
