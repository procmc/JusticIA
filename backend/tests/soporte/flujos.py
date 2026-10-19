"""Soporte de los flujos de la red de seguridad (spec 004, RA-02.13, RA-02.14 y RNF-09.1).

Lo que necesitan las pruebas de los flujos críticos (subir, procesar, chatear, notebooks) sin pausas fijas y sin tocar
nada real:

- `encolado_interceptado`: sustituye el `.delay()` de la tarea de ingesta por un registro de lo que se habría encolado.
  La carga por la API real guarda el archivo (en la carpeta temporal) y devuelve los identificadores `PRUEBA-tarea-<n>`,
  pero no procesa nada.
- `procesamiento_en_prueba`: además ejecuta cada pendiente DESDE EL HILO DE LA PRUEBA con `procesar()`. La tarea usa
  `asyncio.run`, así que no puede correr dentro del bucle de la petición (decisión 1 del plan); por eso se intercepta el
  encolado y se procesa después. Usa los simulados de HTR y audio y los embeddings reales de la integración.
- `exigir_estado` y `exigir_progreso`: miran UNA vez y fallan diciendo qué esperaban y qué encontraron (sin pausas).
- `documento_de_prueba`, `tema_heredado` y `notebook_de_prueba`: datos inventados, con el prefijo `PRUEBA` o registrados
  para que la limpieza (`datos.py`) los alcance aunque no lo lleven (RA-02.14).
- `foto_de_efectos`: lo que hay en la base, Qdrant, la carpeta temporal y los correos, para comprobar «sin efectos».

Este módulo es un plugin de pytest (lo declara el `conftest.py` raíz) y nunca importa `app` al cargarse: lo hace dentro de
las funciones y las fixtures, que solo piden las pruebas de integración.
"""
import itertools
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest

from tests.soporte import entorno, simulados
from tests.soporte.datos import Registro, UsuarioPrueba
from tests.soporte.nombres import PREFIJO_DATOS

_consecutivo_de_tema = itertools.count(1)
_consecutivo_de_notebook = itertools.count(1)


# --- Datos de prueba ---------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class DocumentoPrueba:
    """Un documento de texto inventado: su nombre lleva el prefijo y su contenido una frase distintiva única."""

    nombre: str
    contenido: bytes
    frase: str


def documento_de_prueba() -> DocumentoPrueba:
    """Un `PRUEBA_<uuid8>.txt` con una frase distintiva única, para reconocerlo en fragmentos, contexto y respuestas."""
    sufijo = uuid.uuid4().hex[:8]
    frase = f"la quebrada ficticia {sufijo} desemboca en la laguna inventada de los patos azules"
    texto = (
        f"{PREFIJO_DATOS} documento inventado número {sufijo}. "
        f"Este texto es ficticio y sirve solo para las pruebas automatizadas de ServIA: {frase}. "
        "Describe un expediente imaginario de una oficina que no existe, con fechas, nombres y lugares inventados, "
        "y se repite lo suficiente para formar al menos un fragmento completo cuando el sistema lo divide."
    )
    return DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=texto.encode("utf-8"), frase=frase)


def tema_heredado(registro: Registro) -> str:
    """Un número de tema en formato heredado (`99-NNNNNN-0001-PE`, sin prefijo), ya registrado para que se limpie."""
    numero = f"99-{next(_consecutivo_de_tema):06d}-0001-PE"
    registro.registrar_tema(numero)
    return numero


@dataclass(frozen=True)
class NotebookPrueba:
    """Un notebook propio de prueba: su dueño es un Usuario Gubernamental `PRUEBA`."""

    id: int
    nombre: str
    clave_interna: str
    usuario: UsuarioPrueba


def crear_notebook_de_prueba(usuario: UsuarioPrueba, registro: Registro) -> NotebookPrueba:
    """Crea con el repositorio (no por la API) un notebook `PRUEBA` del usuario y registra su tema `NB-<id>` (RA-02.13 c)."""
    from app.db.database import SessionLocal
    from app.repositories.notebook_repository import NotebookRepository

    nombre = f"{PREFIJO_DATOS} notebook {next(_consecutivo_de_notebook)}"
    with SessionLocal() as db:
        notebook = NotebookRepository().crear(db, nombre, usuario.cedula)
        propio = NotebookPrueba(
            id=notebook.CN_Id_notebook, nombre=notebook.CT_Nombre, clave_interna=notebook.clave_interna, usuario=usuario
        )
    registro.registrar_tema(propio.clave_interna)
    return propio


@pytest.fixture
def notebook_de_prueba(usuario_gubernamental, registro_de_datos) -> NotebookPrueba:
    """Un notebook propio de un Usuario Gubernamental `PRUEBA`, creado sin depender de las pruebas de RF-17.1 (RA-02.13 c)."""
    return crear_notebook_de_prueba(usuario_gubernamental, registro_de_datos)


def crear_notebook(cliente, cabeceras: dict, nombre: str, registro: Registro) -> dict:
    """Crea un notebook POR LA API como lo haría la interfaz y registra su tema `NB-<id>`; devuelve la respuesta (JSON)."""
    if not nombre.startswith(PREFIJO_DATOS):
        raise ValueError(f"El nombre del notebook de prueba debe empezar por {PREFIJO_DATOS!r}: {nombre!r}.")
    respuesta = cliente.post("/notebooks", json={"nombre": nombre}, headers=cabeceras)
    assert respuesta.status_code == 200, f"No se pudo crear el notebook de prueba (código {respuesta.status_code})."
    notebook = respuesta.json()
    registro.registrar_tema(notebook["clave_interna"])
    return notebook


# --- Encolado interceptado y procesamiento dentro de la prueba -------------------------------------------------------------

@dataclass
class Pendiente:
    """Una tarea que la carga habría encolado: su identificador y los argumentos con que se habría ejecutado."""

    id: str
    tema: str
    archivo_info: dict
    usuario: str


class Encolado:
    """Reemplaza `procesar_archivo_celery.delay`: guarda `(tema, archivo_info, usuario)` y devuelve un id `PRUEBA-tarea-<n>`."""

    def __init__(self, registro: Registro):
        self.pendientes: List[Pendiente] = []
        self._registro = registro

    def delay(self, tema, archivo_info, usuario):
        pendiente = Pendiente(id=f"{PREFIJO_DATOS}-tarea-{len(self.pendientes) + 1}", tema=tema,
                              archivo_info=archivo_info, usuario=usuario)
        self.pendientes.append(pendiente)
        # El archivo ya quedó guardado (en la carpeta temporal): se registra para que la limpieza lo borre.
        if archivo_info.get("filepath"):
            self._registro.registrar_archivo(Path(archivo_info["filepath"]))
        return type("TareaInterceptada", (), {"id": pendiente.id})()


@pytest.fixture
def encolado_interceptado(monkeypatch, registro_de_datos) -> Encolado:
    """La carga por la API real guarda el archivo pero no procesa: la tarea queda en `pendientes` (RA-02.13 a)."""
    from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

    encolado = Encolado(registro_de_datos)
    monkeypatch.setattr(procesar_archivo_celery, "delay", encolado.delay)
    return encolado


class Procesamiento:
    """Ejecuta, desde el hilo de la prueba, las tareas que la carga dejó pendientes."""

    def __init__(self, encolado: Encolado):
        self.encolado = encolado
        self.resultados: Dict[str, object] = {}

    def procesar(self) -> Dict[str, object]:
        """Procesa cada pendiente que todavía no se procesó y devuelve el resultado de cada uno, por identificador.

        Usa `apply(..., throw=False)`: un fallo del procesamiento no lanza aquí, queda en el resultado (`state`, `result`)
        y en el seguimiento de progreso, como lo vería el usuario. Cada tarea recibe una copia de sus argumentos porque
        la tarea libera el contenido del archivo al terminar.
        """
        from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery

        nuevos = {}
        for pendiente in self.encolado.pendientes:
            if pendiente.id in self.resultados:
                continue
            resultado = procesar_archivo_celery.apply(
                args=(pendiente.tema, dict(pendiente.archivo_info), pendiente.usuario),
                task_id=pendiente.id,
                throw=False,
            )
            self.resultados[pendiente.id] = nuevos[pendiente.id] = resultado
        return nuevos


@pytest.fixture
def procesamiento_en_prueba(
    encolado_interceptado, celery_inmediato, carpeta_archivos, embeddings_reales, htr_simulado, audio_simulado, monkeypatch
) -> Procesamiento:
    """Subir y procesar dentro de la prueba (RA-02.13 b): `procesar()` corre la tarea real sin worker, sin pausas y con
    HTR y audio simulados (RNF-09.1). La limpieza programada de la tarea (un hilo que duerme minutos) no se programa."""
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    monkeypatch.setattr(progress_manager, "schedule_task_cleanup", lambda *args, **kwargs: None)
    simulados.comprobar_simulados(["htr", "audio"])
    return Procesamiento(encolado_interceptado)


# --- Esperas sin pausas -----------------------------------------------------------------------------------------------------

def estado_del_documento(id_documento: int) -> Optional[str]:
    """El estado de procesamiento del documento («Pendiente», «Procesado», «Error») o `None` si no existe."""
    from app.db.database import SessionLocal
    from app.db.models import T_Documento

    with SessionLocal() as db:
        documento = db.get(T_Documento, id_documento)
        if documento is None or documento.estado_procesamiento is None:
            return None
        return documento.estado_procesamiento.CT_Nombre_estado


def exigir_estado(id_documento: int, estado: str) -> None:
    """Mira el estado del documento UNA vez; si no es `estado`, falla con «se esperaba <estado> y se encontró <x>»."""
    encontrado = estado_del_documento(id_documento)
    assert encontrado == estado, f"Documento {id_documento}: se esperaba {estado} y se encontró {encontrado}."


def exigir_progreso(id_tarea: str, estado: str) -> None:
    """Mira el seguimiento de la tarea UNA vez; si su estado no es `estado`, falla con «se esperaba <estado> y se encontró <x>»."""
    from app.services.ingesta.async_processing.progress_tracker import progress_manager

    seguimiento = progress_manager.get_status(id_tarea)
    encontrado = seguimiento.get("status") if seguimiento else None
    assert encontrado == estado, f"Tarea {id_tarea}: se esperaba {estado} y se encontró {encontrado}."


def id_del_documento(nombre: str) -> Optional[int]:
    """El identificador del documento con ese nombre de archivo, o `None` si todavía no existe."""
    from app.db.database import SessionLocal
    from app.db.models import T_Documento

    with SessionLocal() as db:
        return db.query(T_Documento.CN_Id_documento).filter(T_Documento.CT_Nombre_archivo == nombre).scalar()


# --- Cargas, chat y huellas ---------------------------------------------------------------------------------------------------

def cargar(cliente, cabeceras: dict, tema: str, archivos):
    """Carga como la interfaz: `POST /ingesta/archivos` con el tema y los archivos `(nombre, contenido)`."""
    partes = [("files", (nombre, contenido, "text/plain")) for nombre, contenido in archivos]
    return cliente.post("/ingesta/archivos", data={"CT_Num_expediente": tema}, files=partes, headers=cabeceras)


def leer_eventos(respuesta) -> List[dict]:
    """Los eventos `data: {...}` de una respuesta en flujo (el chat), ya decodificados y en orden."""
    eventos = []
    for linea in respuesta.text.splitlines():
        if linea.startswith("data: "):
            try:
                eventos.append(json.loads(linea[len("data: "):]))
            except json.JSONDecodeError:
                eventos.append({"texto": linea[len("data: "):]})
    return eventos


def contexto_enviado(ollama_simulado) -> str:
    """Lo último que recibió el LLM simulado (pregunta y contexto), para comprobar qué fragmentos le llegaron."""
    assert ollama_simulado.preguntas, "El LLM simulado no recibió ninguna consulta."
    return ollama_simulado.preguntas[-1]


def contar_puntos(tema: Optional[str] = None) -> int:
    """Cuántos puntos hay en la colección de pruebas; con `tema`, solo los de ese `metadata.numero_expediente`."""
    import os

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    cliente = entorno.cliente_qdrant()
    try:
        filtro = None
        if tema is not None:
            filtro = Filter(must=[FieldCondition(key="metadata.numero_expediente", match=MatchValue(value=tema))])
        return int(cliente.count(collection_name=os.environ["QDRANT_COLLECTION_NAME"], count_filter=filtro, exact=True).count)
    finally:
        cliente.close()


def foto_de_efectos(correo_simulado=None) -> dict:
    """Lo que hay ahora: filas de bitácora, documentos, temas y notebooks; puntos; archivos de la carpeta temporal y correos.

    Comparar dos fotos (antes y después) comprueba que una petición rechazada no dejó ningún efecto.
    """
    from sqlalchemy import text

    from app.db.database import engine

    with engine.connect() as conexion:
        filas = {
            tabla: int(conexion.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar())
            for tabla in ("T_Bitacora", "T_Documento", "T_Expediente", "T_Notebook")
        }
    carpeta = simulados.carpeta_temporal_actual()
    archivos = sorted(str(p.relative_to(carpeta)) for p in carpeta.rglob("*") if p.is_file()) if carpeta else []
    return {
        "filas": filas,
        "puntos": contar_puntos(),
        "archivos": archivos,
        "correos": len(correo_simulado.intentos) if correo_simulado is not None else 0,
    }
