"""Pruebas de la spec 006 (ingesta de los documentos de Nexus), T1: el tema se normaliza en el servidor y el rastreo
externo de LangChain queda apagado.

- RF-06.52: el servidor admite un tema de hasta 60 caracteres y rechaza uno de 61 con 400 «El tema indicado no es válido».
- RF-06.53: antes de validar, el servidor quita los espacios al inicio y al final del tema; si ya existe uno igual salvo
  mayúsculas y minúsculas, usa el nombre registrado.
- RNF-09.50: al arrancar, `LANGSMITH_TRACING` y `LANGCHAIN_TRACING_V2` quedan en «false» aunque vengan activas o falten;
  si venían activas se registra un aviso sin valores de claves.

Las tareas posteriores de la spec (fallo de la ingesta, RF-07.52) agregan sus pruebas a este archivo.
Todo es simulado (sin SQL Server, Celery ni disco) y los datos son inventados (prefijo `PRUEBA`).
"""
import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

RAIZ_BACKEND = Path(__file__).resolve().parents[2]
VARIABLES_DE_RASTREO = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2")
USUARIO = {"user_id": "PRUEBA-cedula"}


# --- La ruta de carga con todo simulado ---------------------------------------------------------------------------------

@pytest.fixture
def ruta_de_carga(monkeypatch):
    """Deja `ingestar_archivos` sin SQL Server, Celery ni disco; devuelve lo que la ruta entregó a cada pieza.

    - `clasificar_clave`: el tema no es de un notebook.
    - `resolver_o_crear_tema`: no hay un tema igual registrado (devuelve el recibido).
    - `guardar_archivo` y `delay`: anotan el tema con el que se les llamó.
    """
    from app.routes import ingesta
    from app.services import expediente_service, notebook_service
    from app.services.ingesta.async_processing import celery_tasks

    visto = SimpleNamespace(clasificado=None, guardado=None, encolado=None)

    async def clasificar(self, db, tema, usuario_id):
        visto.clasificado = tema
        return notebook_service.ClaveDeNotebook(tipo="no_es_notebook")

    async def guardar(archivo, tema):
        visto.guardado = tema
        return {"filename": "PRUEBA_archivo.txt", "filepath": f"/tmp/PRUEBA/{tema}/PRUEBA_archivo.txt"}

    def encolar(tema, archivo_info, usuario_id):
        visto.encolado = tema
        return SimpleNamespace(id="PRUEBA-tarea-1")

    monkeypatch.setattr(notebook_service.NotebookService, "clasificar_clave", clasificar)
    monkeypatch.setattr(expediente_service.ExpedienteService, "resolver_o_crear_tema",
                        lambda self, db, tema: tema, raising=False)
    monkeypatch.setattr(ingesta.file_management_service, "guardar_archivo", guardar)
    monkeypatch.setattr(celery_tasks.procesar_archivo_celery, "delay", encolar)
    monkeypatch.setattr(ingesta.ingesta_audit_service, "registrar_ingesta", AsyncMock())
    monkeypatch.setattr(ingesta.ingesta_audit_service, "registrar_carga_rechazada", AsyncMock())
    return visto


def _cargar(tema: str):
    from app.routes.ingesta import ingestar_archivos
    import asyncio

    return asyncio.run(ingestar_archivos(
        CT_Num_expediente=tema, files=[MagicMock(filename="PRUEBA_archivo.txt")], db=MagicMock(), current_user=USUARIO))


@pytest.mark.requisito("RF-06.52")
def test_tema_de_61_caracteres_400(ruta_de_carga):
    """RF-06.52: 60 caracteres se aceptan y 61 se rechazan con 400 «El tema indicado no es válido», sin guardar ni encolar."""
    assert _cargar("a" * 60)["expediente"] == "a" * 60
    ruta_de_carga.guardado = ruta_de_carga.encolado = None

    with pytest.raises(HTTPException) as error:
        _cargar("a" * 61)

    assert error.value.status_code == 400
    assert error.value.detail == "El tema indicado no es válido"
    assert ruta_de_carga.guardado is None and ruta_de_carga.encolado is None


@pytest.mark.requisito("RF-06.53")
@pytest.mark.parametrize("recibido", [" PRUEBA Normativa", "PRUEBA Normativa ", "  PRUEBA Normativa  "])
def test_tema_se_recorta(ruta_de_carga, recibido):
    """RF-06.53: los espacios al inicio y al final se quitan antes de clasificar, validar, guardar y encolar (hoy un tema
    que termina en espacio se rechaza)."""
    respuesta = _cargar(recibido)

    assert ruta_de_carga.clasificado == "PRUEBA Normativa"
    assert ruta_de_carga.guardado == "PRUEBA Normativa" and ruta_de_carga.encolado == "PRUEBA Normativa"
    assert respuesta["expediente"] == "PRUEBA Normativa"


@pytest.mark.requisito("RF-06.53")
def test_tema_usa_el_nombre_registrado():
    """RF-06.53: si ya hay un tema igual salvo mayúsculas, el servicio devuelve el nombre registrado; si no, el recibido
    (las tildes distinguen temas, R5)."""
    from app.services.expediente_service import ExpedienteService

    servicio = ExpedienteService()
    servicio.expediente_repo = MagicMock()
    servicio.expediente_repo.obtener_por_nombre_sin_mayusculas.return_value = SimpleNamespace(CT_Num_expediente="PRUEBA Normativa")
    assert servicio.nombre_de_tema_registrado(MagicMock(), "prueba normativa") == "PRUEBA Normativa"

    servicio.expediente_repo.obtener_por_nombre_sin_mayusculas.return_value = None
    assert servicio.nombre_de_tema_registrado(MagicMock(), "PRUEBA Normatíva") == "PRUEBA Normatíva"


@pytest.mark.requisito("RF-06.53")
def test_tema_en_carrera_usa_el_registrado():
    """RF-06.53 (T10): si otra petición creó el tema entre la lectura y el alta (la restricción única rechaza la segunda con
    `IntegrityError`), el servicio hace rollback y devuelve el nombre registrado por la que ganó."""
    from sqlalchemy.exc import IntegrityError
    from app.services.expediente_service import ExpedienteService

    servicio = ExpedienteService()
    servicio.expediente_repo = MagicMock()
    servicio.expediente_repo.obtener_por_nombre_sin_mayusculas.side_effect = [
        None, SimpleNamespace(CT_Num_expediente="PRUEBA Carrera")]
    servicio.expediente_repo.crear_tema.side_effect = IntegrityError("INSERT", {}, Exception("uq_expediente_num"))
    db = MagicMock()

    assert servicio.resolver_o_crear_tema(db, "prueba carrera") == "PRUEBA Carrera"
    db.rollback.assert_called_once()


@pytest.mark.requisito("RF-06.53")
def test_tema_nuevo_se_crea_y_el_registrado_no_se_repite():
    """RF-06.53 (T10): un tema nuevo se crea con la grafía recibida; uno ya registrado (otra grafía) no se vuelve a crear."""
    from app.services.expediente_service import ExpedienteService

    servicio = ExpedienteService()
    servicio.expediente_repo = MagicMock()
    servicio.expediente_repo.obtener_por_nombre_sin_mayusculas.return_value = None
    assert servicio.resolver_o_crear_tema(MagicMock(), "PRUEBA Nuevo") == "PRUEBA Nuevo"
    servicio.expediente_repo.crear_tema.assert_called_once()

    servicio.expediente_repo = MagicMock()
    servicio.expediente_repo.obtener_por_nombre_sin_mayusculas.return_value = SimpleNamespace(CT_Num_expediente="PRUEBA Nuevo")
    assert servicio.resolver_o_crear_tema(MagicMock(), "prueba nuevo") == "PRUEBA Nuevo"
    servicio.expediente_repo.crear_tema.assert_not_called()


# --- RNF-09.50: el rastreo externo queda apagado ------------------------------------------------------------------------------

@pytest.mark.requisito("RNF-09.50")
def test_rastreo_activo_se_apaga_con_aviso(monkeypatch, caplog):
    """RNF-09.50: con ambas variables en «true» quedan en «false» y se registra un aviso que las nombra, sin valores de
    claves."""
    from app.config.config import apagar_rastreo_externo

    for nombre in VARIABLES_DE_RASTREO:
        monkeypatch.setenv(nombre, "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "PRUEBA-clave-inventada-7731")

    with caplog.at_level(logging.WARNING):
        apagar_rastreo_externo()

    assert [os.environ[n] for n in VARIABLES_DE_RASTREO] == ["false", "false"]
    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    texto = avisos[0].getMessage()
    assert all(n in texto for n in VARIABLES_DE_RASTREO)
    assert "PRUEBA-clave-inventada-7731" not in caplog.text


@pytest.mark.requisito("RNF-09.50")
def test_rastreo_ausente_se_apaga_sin_aviso(monkeypatch, caplog):
    """RNF-09.50: con las variables ausentes (o ya en «false») quedan en «false» y no se registra ningún aviso."""
    from app.config.config import apagar_rastreo_externo

    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")

    with caplog.at_level(logging.WARNING):
        apagar_rastreo_externo()

    assert [os.environ[n] for n in VARIABLES_DE_RASTREO] == ["false", "false"]
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


@pytest.mark.requisito("RNF-09.50")
def test_rastreo_se_apaga_al_importar_la_configuracion():
    """RNF-09.50: el arranque (la importación de la configuración, que usan el backend y el proceso de ingesta) deja el
    rastreo apagado aunque el entorno lo traiga activo."""
    entorno = {**os.environ, "LANGSMITH_TRACING": "true", "LANGCHAIN_TRACING_V2": "true"}
    resultado = subprocess.run(
        [sys.executable, "-c",
         "import os, app.config.config; print(os.environ['LANGSMITH_TRACING'], os.environ['LANGCHAIN_TRACING_V2'])"],
        cwd=RAIZ_BACKEND, env=entorno, capture_output=True, text=True, timeout=60)

    assert resultado.returncode == 0, resultado.stderr[-500:]
    assert resultado.stdout.strip().splitlines()[-1] == "false false"


# --- RF-07.52 (T2): el fallo se informa con un texto fijo y la causa clasificada ------------------------------------------------

TEXTO_FIJO = "No se pudo procesar el archivo. Por favor, intente nuevamente."
CRUDO_CON_DETALLE = "Error extrayendo texto de PRUEBA.pdf (tipo: .pdf): detalle-interno-PRUEBA en /app/uploads/PRUEBA/interno.bin"


@pytest.mark.requisito("RF-07.52")
def test_marcar_fallo_texto_fijo_y_causa():
    """RF-07.52: `marcar_fallo` deja como mensaje el texto fijo más la causa clasificada y como detalle solo la causa; el
    texto crudo de la excepción y las rutas del servidor no llegan al seguimiento."""
    from app.services.ingesta.async_processing.progress_tracker import ProgressTracker

    seguimiento = ProgressTracker.__new__(ProgressTracker)
    seguimiento.task_id = "PRUEBA-tarea"
    seguimiento.mark_failed = MagicMock()

    seguimiento.marcar_fallo(CRUDO_CON_DETALLE)

    (mensaje,), detalle = seguimiento.mark_failed.call_args
    assert mensaje == f"{TEXTO_FIJO} Causa: no se pudo extraer el texto."
    assert detalle == {"error_details": "no se pudo extraer el texto"}
    assert "detalle-interno" not in mensaje and "/app/" not in mensaje


@pytest.mark.requisito("RF-07.52")
def test_marcar_fallo_sin_crudo_es_error_interno():
    """RF-07.52: sin texto de error o con uno que no encaja, la causa es «error interno»."""
    from app.services.ingesta.async_processing.progress_tracker import ProgressTracker

    seguimiento = ProgressTracker.__new__(ProgressTracker)
    seguimiento.task_id = "PRUEBA-tarea"
    seguimiento.mark_failed = MagicMock()

    seguimiento.marcar_fallo(None)

    assert seguimiento.mark_failed.call_args.args[0] == f"{TEXTO_FIJO} Causa: error interno."


@pytest.mark.requisito("RF-07.52")
def test_rama_failure_del_progreso_usa_el_texto_fijo(monkeypatch):
    """RF-07.52: si no hay seguimiento y Celery informa FAILURE, la ruta de progreso devuelve el texto fijo con la causa,
    nunca `str(result.info)`."""
    import asyncio

    from app.routes import ingesta
    from app.services.ingesta.async_processing import progress_tracker

    monkeypatch.setattr(progress_tracker.progress_manager, "get_status", lambda task_id: None)
    resultado = SimpleNamespace(state="FAILURE", info=ValueError(CRUDO_CON_DETALLE))
    monkeypatch.setattr(ingesta, "AsyncResult", lambda task_id: resultado)

    respuesta = asyncio.run(ingesta.consultar_progreso_tarea("PRUEBA-tarea", current_user=USUARIO))

    assert respuesta["status"] == "fallido" and respuesta["ready"] is True
    assert respuesta["message"] == f"{TEXTO_FIJO} Causa: no se pudo extraer el texto."
    assert "detalle-interno" not in respuesta["message"] and "/app/" not in respuesta["message"]
