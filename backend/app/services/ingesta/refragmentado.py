"""Re-fragmentado de los documentos de uno o más temas (RF-08.63, RN-01.60).

Procedimiento del desarrollador, no una acción de usuario: no tiene ruta ni tarea de Celery ni bitácora (plan §12, D-8).
Vuelve a fragmentar, con la configuración actual (`contexto_config`), solo los documentos en estado Procesado de los
temas indicados, leyendo el archivo guardado. Conserva la fila, el tema, el archivo y el estado del documento, y en cada
fragmento el documento, el tema, el archivo, las fechas originales y la ruta.

Uso (en el contenedor del backend):

    python -m app.services.ingesta.refragmentado --tema "TEMA-1" --tema "TEMA-2" [--simular]

* `--tema` es obligatorio y se puede repetir; no existe una opción «todos».
* `--simular` solo informa cuántos documentos y fragmentos tocaría, sin cambiar nada.
* Seguro: fuera de `servia_pruebas` (base y colección), la corrida real se niega salvo con `--confirmar-desarrollo`,
  que solo se usa con aprobación expresa (T12).

Por cada documento: se guardan los fragmentos nuevos (con identificador propio) y, solo si todo salió bien, se borran los
anteriores y cualquier otro fragmento del documento (también limpia los repetidos de una corrida fallida). Si algo falla
(archivo faltante, extracción, inserción), se borran los nuevos que alcanzaron a guardarse, quedan los anteriores y se
informa; el siguiente documento se procesa igual. Es idempotente: una segunda corrida deja el mismo número de fragmentos.
"""
import argparse
import asyncio
import logging
import mimetypes
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import config
from app.db import database
from app.repositories.documento_repository import DocumentoRepository
from app.services.documentos.file_management_service import file_management_service
from app.services.ingesta.file_management.document_processor import extract_text_from_file
from app.vectorstore import get_vectorstore_backend
from app.vectorstore.storage import store_in_vectorstore

logger = logging.getLogger(__name__)

# Nombre completo de la base y la colección de pytest (igual que la protección de `tests/soporte/nombres.py`).
_NOMBRE_PRUEBAS = "servia_pruebas"

# Claves de `meta` que `store_in_vectorstore` calcula de nuevo para cada fragmento.
_META_CALCULADA = ("total_chunks", "chunk_index", "chunk_length", "estimated_pages")


@dataclass
class FalloDocumento:
    id_documento: int
    nombre_archivo: str
    causa: str


@dataclass
class Informe:
    temas: List[str] = field(default_factory=list)
    simulacion: bool = False
    documentos: int = 0
    fragmentos_actuales: int = 0
    fragmentos_nuevos: int = 0
    fallidos: List[FalloDocumento] = field(default_factory=list)


def _documentos_de(temas: List[str]) -> list:
    """Los documentos Procesado de los temas, una vez cada uno: (id, nombre, número del tema, id del tema)."""
    with database.SessionLocal() as db:
        filas = DocumentoRepository().listar_procesados_de_temas(db, temas)
    vistos, unicos = set(), []
    for fila in filas:
        if fila[0] not in vistos:
            vistos.add(fila[0])
            unicos.append(fila)
    return unicos


async def _borrar_salvo(id_documento: int, conservar: set) -> None:
    """Borra los puntos del documento cuyo id no está en `conservar`."""
    backend = get_vectorstore_backend()
    sobrantes = [p["id"] for p in await backend.listar_puntos_de_documento(id_documento) if p["id"] not in conservar]
    await backend.borrar_por_ids(sobrantes)


async def _refragmentar_documento(id_documento: int, nombre: str, tema: str, id_tema: int, viejos: list) -> int:
    """Vuelve a fragmentar un documento; devuelve cuántos fragmentos nuevos quedaron."""
    ids_viejos = {p["id"] for p in viejos}
    primero = min(viejos, key=lambda p: p["metadata"].get("indice_chunk", 0)) if viejos else None
    metadata = primero["metadata"] if primero else {}
    meta = {k: v for k, v in (metadata.get("meta") or {}).items() if k not in _META_CALCULADA}
    nombre_archivo = metadata.get("nombre_archivo") or nombre
    meta["nombre_archivo"] = nombre_archivo
    numero_tema = metadata.get("numero_expediente") or tema

    try:
        ruta = file_management_service.obtener_ruta_archivo(tema, nombre)
        if ruta is None or not ruta.is_file():
            raise FileNotFoundError(f"no se encontró el archivo guardado «{nombre}» del tema «{tema}»")
        contenido = ruta.read_bytes()
        texto = await extract_text_from_file(contenido, nombre, mimetypes.guess_type(nombre)[0] or "application/octet-stream")
        if not texto or not texto.strip():
            raise ValueError("no se pudo extraer texto del archivo")
        ids_nuevos, cantidad = await store_in_vectorstore(
            texto=texto,
            metadatos=meta,
            CT_Num_expediente=numero_tema,
            id_expediente=metadata.get("id_expediente", id_tema),
            id_documento=id_documento,
            ids_propios=True,
            fecha_carga=metadata.get("fecha_carga"),
            fecha_expediente_creacion=metadata.get("fecha_expediente_creacion"),
        )
        if not ids_nuevos:
            raise ValueError("el texto no produjo fragmentos")
    except Exception:
        # Quedan solo los anteriores: se borra lo nuevo que alcanzó a guardarse.
        await _borrar_salvo(id_documento, ids_viejos)
        raise
    await _borrar_salvo(id_documento, {str(i) for i in ids_nuevos})
    return cantidad


def _es_entorno_de_pruebas() -> bool:
    """Verdadero solo si la base y la colección activas son, con el nombre completo exacto, las de pytest."""
    return (config.SQL_SERVER_DATABASE == _NOMBRE_PRUEBAS
            and config.QDRANT_COLLECTION_NAME == _NOMBRE_PRUEBAS)


def _mensaje_negativa() -> str:
    return (f"La base «{config.SQL_SERVER_DATABASE}» y la colección «{config.QDRANT_COLLECTION_NAME}» no son las de "
            f"pruebas («{_NOMBRE_PRUEBAS}»): la corrida real cambiaría datos de desarrollo. Use --simular para solo "
            "informar o --confirmar-desarrollo para ejecutarla con aprobación expresa.")


class EjecucionNoPermitida(RuntimeError):
    """La corrida real se pidió fuera del entorno de pruebas sin confirmar."""


async def refragmentar(temas: List[str], simular: bool = False, confirmar_desarrollo: bool = False) -> Informe:
    """Re-fragmenta los documentos Procesado de `temas`. Con `simular`, solo informa.

    Seguro: fuera de `servia_pruebas`, la corrida real exige `confirmar_desarrollo=True` (T12, con aprobación)."""
    if not temas:
        raise ValueError("Se necesita al menos un tema")
    if not simular and not confirmar_desarrollo and not _es_entorno_de_pruebas():
        raise EjecucionNoPermitida(_mensaje_negativa())
    informe = Informe(temas=list(temas), simulacion=simular)
    backend = get_vectorstore_backend()
    documentos = _documentos_de(list(temas))
    informe.documentos = len(documentos)
    previos = {}
    for id_documento, *_ in documentos:
        previos[id_documento] = await backend.listar_puntos_de_documento(id_documento)
        informe.fragmentos_actuales += len(previos[id_documento])
    if simular:
        return informe

    for id_documento, nombre, tema, id_tema in documentos:
        try:
            informe.fragmentos_nuevos += await _refragmentar_documento(
                id_documento, nombre, tema, id_tema, previos[id_documento])
        except Exception as error:
            causa = f"{type(error).__name__}: {error}"
            logger.error("Re-fragmentado fallido del documento %s (%s): %s", id_documento, nombre, causa)
            informe.fallidos.append(FalloDocumento(id_documento, nombre, causa))
    return informe


def _imprimir(informe: Informe) -> None:
    modo = "SIMULACIÓN (no se cambió nada)" if informe.simulacion else "Re-fragmentado"
    lineas = [
        f"{modo}: temas {', '.join(informe.temas)}",
        f"  Documentos Procesado: {informe.documentos}",
        f"  Fragmentos actuales: {informe.fragmentos_actuales}",
    ]
    if not informe.simulacion:
        lineas.append(f"  Fragmentos nuevos: {informe.fragmentos_nuevos}")
        lineas.append(f"  Documentos fallidos: {len(informe.fallidos)}")
        lineas.extend(f"    - {f.id_documento} {f.nombre_archivo}: {f.causa}" for f in informe.fallidos)
    for linea in lineas:
        print(linea)
        logger.info(linea)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.ingesta.refragmentado",
        description="Vuelve a fragmentar los documentos Procesado de los temas indicados (RF-08.63).")
    parser.add_argument("--tema", action="append", required=True, metavar="NUMERO",
                        help="número del tema; obligatorio y repetible")
    parser.add_argument("--simular", action="store_true", help="solo informa, sin cambiar nada")
    parser.add_argument("--confirmar-desarrollo", action="store_true",
                        help="permite la corrida real fuera de servia_pruebas (solo con aprobación expresa)")
    argumentos = parser.parse_args(argv)
    if not argumentos.simular and not argumentos.confirmar_desarrollo and not _es_entorno_de_pruebas():
        parser.error(_mensaje_negativa())
    inicio = time.time()
    informe = asyncio.run(refragmentar(argumentos.tema, simular=argumentos.simular,
                                       confirmar_desarrollo=argumentos.confirmar_desarrollo))
    _imprimir(informe)
    print(f"  Duración: {time.time() - inicio:.1f} s")
    return 1 if informe.fallidos else 0


if __name__ == "__main__":
    sys.exit(main())
