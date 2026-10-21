"""
Rutas REST para Notebooks (NotebookServIA).

Endpoints:
    - POST /notebooks: Crear un notebook nuevo
    - GET /notebooks: Listar los notebooks del usuario autenticado
    - GET /notebooks/{id}/documentos: Listar los documentos de un notebook propio
    - GET /notebooks/{id}/documentos/{id}/archivo: Previsualizar el archivo de un documento
    - DELETE /notebooks/{id}/documentos/{id}: Quitar un documento del notebook

Las rutas solo reciben, llaman al servicio, registran en la bitácora y traducen los errores (RF-17.33): el acceso a datos,
a Qdrant y a los archivos está en `NotebookService`. Un notebook, o un documento, ajeno o inexistente da el mismo 404 y deja
un intento fallido solo con su motivo (RNF-07.6, RNF-07.32, RF-21.32).

Los documentos se suben a un notebook reutilizando el endpoint ya
existente POST /ingesta/archivos, pasando la clave_interna del
notebook (ej. "NB-7") como CT_Num_expediente — ver
app.db.models.notebook.T_Notebook.clave_interna.

Ver también:
    * app.services.notebook_service: Lógica de negocio
    * app.services.bitacora.notebooks_audit_service: Registro en la bitácora (RF-21.30, RF-21.32)
    * app.routes.ingesta: Reutilizado para subir documentos a un notebook
    * app.routes.rag: Chat acotado a un notebook (notebook_id)

Authors:
    ServIA Team

Version:
    1.1.0
"""

import logging
import mimetypes
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.constants.tipos_accion import TiposAccion
from app.db.database import get_db
from app.auth.jwt_auth import require_usuario_judicial
from app.services.bitacora.notebooks_audit_service import MOTIVO_NOTEBOOK_NO_DISPONIBLE, notebooks_audit_service
from app.services.notebook_service import (
    ArchivoNoEncontrado, DocumentoSinProcesar, ErrorAlQuitar, NotebookService, RecursoNoDisponible
)

logger = logging.getLogger(__name__)

router = APIRouter()
notebook_service = NotebookService()


class NotebookCrearRequest(BaseModel):
    nombre: str


class NotebookResponse(BaseModel):
    id: int
    nombre: str
    clave_interna: str
    fecha_creacion: str


def _to_response(notebook) -> NotebookResponse:
    return NotebookResponse(
        id=notebook.CN_Id_notebook,
        nombre=notebook.CT_Nombre,
        clave_interna=notebook.clave_interna,
        fecha_creacion=notebook.CF_Fecha_creacion.isoformat(),
    )


@router.post("", response_model=NotebookResponse)
async def crear_notebook(
    request: NotebookCrearRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Crea un notebook nuevo para el usuario autenticado."""
    try:
        notebook = await notebook_service.crear_notebook(
            db=db, nombre=request.nombre, usuario_id=current_user["user_id"]
        )
    except ValueError as e:
        # El nombre vacío: su mensaje es para el usuario (RF-17.1).
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Sin el texto de la excepción ni en la respuesta ni en el registro: puede traer rutas internas o lo escrito por el
        # usuario (RF-17.30). El registro conserva el tipo del error y su traza para diagnosticarlo.
        logger.error(
            "Error creando el notebook (%s)\n%s", type(e).__name__, "".join(traceback.format_tb(e.__traceback__))
        )
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    await notebooks_audit_service.registrar_creacion(db, current_user["user_id"], notebook.clave_interna)
    return _to_response(notebook)


@router.get("", response_model=list[NotebookResponse])
async def listar_notebooks(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Lista los notebooks del usuario autenticado, más reciente primero."""
    notebooks = await notebook_service.listar_notebooks_usuario(db, current_user["user_id"])
    return [_to_response(n) for n in notebooks]


class DocumentoNotebookResponse(BaseModel):
    id: int
    nombre_archivo: str
    estado: str


async def _no_encontrado(db: Session, current_user: dict, no_disponible: RecursoNoDisponible, tipo_accion_id: int):
    """Deja el intento fallido de la acción (solo con su motivo, RF-21.32) y devuelve el 404 uniforme: el mismo para lo
    ajeno y lo inexistente (RNF-07.6)."""
    await notebooks_audit_service.registrar_intento_fallido(
        db=db, usuario_id=current_user["user_id"], tipo_accion_id=tipo_accion_id, motivo=no_disponible.motivo
    )
    if no_disponible.motivo == MOTIVO_NOTEBOOK_NO_DISPONIBLE:
        return HTTPException(status_code=404, detail="Notebook no encontrado")
    return HTTPException(status_code=404, detail="Documento no encontrado en este notebook")


@router.get("/{notebook_id}/documentos", response_model=list[DocumentoNotebookResponse])
async def listar_documentos_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Lista los documentos ya subidos y procesados de un notebook."""
    try:
        documentos = await notebook_service.listar_documentos_de_notebook(db, notebook_id, current_user["user_id"])
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user, no_disponible, TiposAccion.LISTAR_ARCHIVOS)

    return [
        DocumentoNotebookResponse(
            id=d.CN_Id_documento,
            nombre_archivo=d.CT_Nombre_archivo,
            estado=d.estado_procesamiento.CT_Nombre_estado if d.estado_procesamiento else "Desconocido",
        )
        for d in documentos
    ]


@router.get("/{notebook_id}/documentos/{documento_id}/archivo")
async def ver_archivo_documento_notebook(
    notebook_id: int,
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """
    Sirve el archivo original de un documento del notebook para previsualizarlo
    (imagen o PDF renderizado inline en el navegador, no forzado a descarga).
    """
    try:
        notebook, documento, ruta_archivo = await notebook_service.obtener_archivo_de_documento(
            db, notebook_id, documento_id, current_user["user_id"]
        )
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user, no_disponible, TiposAccion.DESCARGAR_ARCHIVO)
    except DocumentoSinProcesar as error:
        await notebooks_audit_service.registrar_previsualizacion_fallida(
            db, current_user["user_id"], error.clave, error.documento_id, "documento sin procesar", "validacion"
        )
        raise HTTPException(status_code=400, detail="El archivo aún no está disponible para previsualizar")
    except ArchivoNoEncontrado as error:
        await notebooks_audit_service.registrar_previsualizacion_fallida(
            db, current_user["user_id"], error.clave, error.documento_id, "archivo no encontrado", "interno"
        )
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    await notebooks_audit_service.registrar_previsualizacion(
        db, current_user["user_id"], notebook.clave_interna, documento.CN_Id_documento
    )
    media_type, _ = mimetypes.guess_type(documento.CT_Nombre_archivo)
    return FileResponse(path=str(ruta_archivo), media_type=media_type or "application/octet-stream")


@router.delete("/{notebook_id}/documentos/{documento_id}")
async def eliminar_documento_notebook(
    notebook_id: int,
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Quita un documento de un notebook: chunks de Qdrant, archivo físico y registro en BD."""
    try:
        notebook = await notebook_service.quitar_documento(db, notebook_id, documento_id, current_user["user_id"])
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user, no_disponible, TiposAccion.QUITAR_DOCUMENTO_NOTEBOOK)
    except ErrorAlQuitar as error:
        # El fallo queda en la bitácora y en el registro del servidor solo con el tipo y la traza, sin el texto de la
        # excepción (puede traer rutas internas, RF-19.2); el documento sigue listado y el reintento completa lo que faltó.
        await notebooks_audit_service.registrar_quitar(
            db, current_user["user_id"], error.clave, error.documento_id, exito=False, tipo_error="interno"
        )
        causa = error.causa
        logger.error(
            "Error quitando un documento de un notebook (%s)\n%s",
            type(causa).__name__,
            "".join(traceback.format_tb(causa.__traceback__)),
        )
        raise HTTPException(status_code=500, detail="No se pudo quitar el documento. Intente de nuevo.")

    await notebooks_audit_service.registrar_quitar(
        db, current_user["user_id"], notebook.clave_interna, documento_id, exito=True
    )
    return {"message": "Documento eliminado", "documento_id": documento_id}
