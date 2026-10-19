"""Pruebas de T1 (spec 004): el soporte de los flujos (RA-02.13, RA-02.14 y RNF-09.1).

Comprueban las piezas que usarán las pruebas de los flujos críticos: subir por la API real con el encolado interceptado,
subir y procesar dentro de la prueba sin pausas, un notebook propio de prueba y la limpieza ampliada (tema heredado,
`NB-<id>` y conversaciones). Todo ocurre en la carpeta temporal, con la base y la colección `servia_pruebas`, el Redis
simulado y HTR y audio simulados; los datos son inventados (prefijo `PRUEBA` o temas registrados).
"""
import threading
from pathlib import Path

import pytest

from tests.soporte import datos, flujos, simulados
from tests.soporte.flujos import (
    cargar, contar_puntos, crear_notebook, documento_de_prueba, exigir_estado, exigir_progreso, foto_de_efectos,
    id_del_documento, tema_heredado,
)

# La tarea de ingesta consulta su estado en Celery; en modo inmediato Celery avisa que ese resultado no se guarda en el
# backend. Es un aviso del propio sistema en un modo que nunca usa en producción (como en `test_celery_inmediato.py`).
pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


@pytest.mark.requisito("RA-02.13")
def test_subir_con_encolado_interceptado(cliente_api, sesion, usuario_gubernamental, registro_de_datos, carpeta_archivos,
                                         encolado_interceptado):
    """RA-02.13 (a): la carga por la API real guarda el archivo en la carpeta temporal, deja la tarea pendiente y no procesa nada."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    antes = foto_de_efectos()

    respuesta = cargar(cliente_api, sesion, tema, [(documento.nombre, documento.contenido)])

    assert respuesta.status_code == 200
    assert respuesta.json()["task_ids"] == ["PRUEBA-tarea-1"]
    [pendiente] = encolado_interceptado.pendientes
    assert (pendiente.id, pendiente.tema, pendiente.usuario) == ("PRUEBA-tarea-1", tema, usuario_gubernamental.cedula)
    assert pendiente.archivo_info["filename"] == documento.nombre
    assert pendiente.archivo_info["content"] == documento.contenido
    ruta = Path(pendiente.archivo_info["filepath"])
    assert ruta.is_file() and carpeta_archivos in ruta.parents  # nunca el `uploads/` de desarrollo

    despues = foto_de_efectos()
    assert despues["filas"]["T_Documento"] == antes["filas"]["T_Documento"]
    assert despues["filas"]["T_Expediente"] == antes["filas"]["T_Expediente"]
    assert despues["puntos"] == antes["puntos"] == 0 and contar_puntos(tema) == 0
    assert len(despues["archivos"]) == len(antes["archivos"]) + 1  # solo el archivo guardado


@pytest.mark.requisito("RA-02.13")
@pytest.mark.requisito("RNF-09.1")
def test_subir_y_procesar_sin_pausas(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, htr_simulado,
                                     audio_simulado):
    """RA-02.13 (b) y RNF-09.1: `procesar()` corre la tarea real desde la prueba; el documento queda Procesado con sus fragmentos."""
    tema = tema_heredado(registro_de_datos)
    documento = documento_de_prueba()
    respuesta = cargar(cliente_api, sesion, tema, [(documento.nombre, documento.contenido)])
    [id_tarea] = respuesta.json()["task_ids"]
    assert id_del_documento(documento.nombre) is None and contar_puntos(tema) == 0  # todavía no se procesó

    resultados = procesamiento_en_prueba.procesar()

    assert list(resultados) == [id_tarea] and resultados[id_tarea].state == "SUCCESS"
    id_documento = id_del_documento(documento.nombre)
    assert id_documento is not None
    exigir_estado(id_documento, "Procesado")
    exigir_progreso(id_tarea, "completado")
    assert contar_puntos(tema) > 0
    assert procesamiento_en_prueba.procesar() == {}  # lo ya procesado no se repite

    # Sin pausas: cada espera mira una vez y dice qué esperaba y qué encontró; la limpieza programada no crea hilos.
    with pytest.raises(AssertionError, match="se esperaba Error y se encontró Procesado"):
        exigir_estado(id_documento, "Error")
    with pytest.raises(AssertionError, match="se esperaba error y se encontró completado"):
        exigir_progreso(id_tarea, "error")
    assert not [hilo for hilo in threading.enumerate() if "delayed_cleanup" in hilo.name]

    # RNF-09.1: el texto no pasó por el HTR ni por la transcripción de audio, y ambos siguen siendo simulados.
    assert htr_simulado.llamadas == [] and audio_simulado.llamadas == []
    simulados.comprobar_simulados(["htr", "audio"])


@pytest.mark.requisito("RA-02.13")
def test_notebook_de_prueba_propio(cliente_api, iniciar_sesion, notebook_de_prueba, registro_de_datos, carpeta_archivos,
                                   encolado_interceptado):
    """RA-02.13 (c): un notebook `PRUEBA` de un usuario `PRUEBA`, con su tema `NB-<id>` registrado, que el dueño puede usar."""
    notebook = notebook_de_prueba
    assert notebook.nombre.startswith("PRUEBA") and notebook.usuario.cedula.startswith("PRUEBA")
    assert notebook.clave_interna == f"NB-{notebook.id}"
    assert notebook.clave_interna in registro_de_datos.temas

    cabeceras = iniciar_sesion(notebook.usuario)
    listado = cliente_api.get("/notebooks", headers=cabeceras)
    assert listado.status_code == 200
    assert [(n["id"], n["clave_interna"]) for n in listado.json()] == [(notebook.id, notebook.clave_interna)]

    documento = documento_de_prueba()
    respuesta = cargar(cliente_api, cabeceras, notebook.clave_interna, [(documento.nombre, documento.contenido)])
    assert respuesta.status_code == 200
    assert [p.tema for p in encolado_interceptado.pendientes] == [notebook.clave_interna]


@pytest.mark.requisito("RA-02.13")
def test_el_notebook_de_prueba_no_depende_de_la_api_de_notebooks(monkeypatch, usuario_gubernamental, registro_de_datos):
    """RA-02.13 (c): se crea por el repositorio; aunque la creación por la API falle, el notebook propio se obtiene igual."""
    from app.services.notebook_service import NotebookService

    def _prohibido(*args, **kwargs):
        raise AssertionError("El notebook de prueba no debe crearse por la API de notebooks.")

    monkeypatch.setattr(NotebookService, "crear_notebook", _prohibido)

    notebook = flujos.crear_notebook_de_prueba(usuario_gubernamental, registro_de_datos)

    assert notebook.clave_interna == f"NB-{notebook.id}" and notebook.clave_interna in registro_de_datos.temas


@pytest.mark.requisito("RA-02.13")
def test_crear_notebook_por_la_api_registra_su_tema(cliente_api, sesion, registro_de_datos):
    """El apoyo `crear_notebook` crea por la API como la interfaz y registra el tema `NB-<id>` para la limpieza."""
    notebook = crear_notebook(cliente_api, sesion, "PRUEBA notebook por la API", registro_de_datos)

    assert notebook["clave_interna"] == f"NB-{notebook['id']}"
    assert notebook["clave_interna"] in registro_de_datos.temas
    with pytest.raises(ValueError):
        crear_notebook(cliente_api, sesion, "sin prefijo", registro_de_datos)


@pytest.mark.requisito("RA-02.14")
def test_residuos_con_tema_heredado_nb_y_conversacion(cliente_api, sesion, usuario_gubernamental, notebook_de_prueba,
                                                      registro_de_datos, procesamiento_en_prueba, destino_de_pruebas):
    """RA-02.14: lo que deja un flujo en un tema heredado, en `NB-<id>` y en una conversación se cuenta y la limpieza lo borra."""
    from app.services.RAG.session_store import conversation_store

    tema = tema_heredado(registro_de_datos)
    en_tema, en_notebook = documento_de_prueba(), documento_de_prueba()
    assert cargar(cliente_api, sesion, tema, [(en_tema.nombre, en_tema.contenido)]).status_code == 200
    assert cargar(cliente_api, sesion, notebook_de_prueba.clave_interna,
                  [(en_notebook.nombre, en_notebook.contenido)]).status_code == 200
    procesamiento_en_prueba.procesar()
    conversation_store.get_session_history(f"session_{usuario_gubernamental.cedula}_1")

    residuos = datos.contar_residuos(destino_de_pruebas)

    assert residuos.hay
    assert residuos.filas["T_Expediente"] == 2 and residuos.filas["T_Documento"] == 2
    assert residuos.filas["T_Expediente_Documento"] == 2 and residuos.filas["T_Notebook"] == 1
    assert residuos.puntos > 0 and residuos.conversaciones == 1
    assert "conversaciones del chat en memoria: 1" in residuos.texto()

    datos.limpiar(destino_de_pruebas, registro_de_datos)

    despues = datos.contar_residuos(destino_de_pruebas)
    assert not despues.hay and despues.texto() == "ninguno"
