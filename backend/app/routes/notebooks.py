"""
Rutas REST para Notebooks (NotebookServIA).

Endpoints:
    - POST /notebooks: Crear un notebook nuevo
    - PUT /notebooks/{id}: Renombrar un notebook propio
    - DELETE /notebooks/{id}: Eliminar (de forma lógica) un notebook propio
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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.constants.tipos_accion import TiposAccion
from app.db.database import get_db
from app.auth.jwt_auth import require_usuario_judicial
from app.services.bitacora.notebooks_audit_service import MOTIVO_NOTEBOOK_NO_DISPONIBLE, notebooks_audit_service
from app.services.notebook_service import (
    ArchivoNoEncontrado, DocumentoSinProcesar, ErrorAlQuitar, NombreNoValido, NotebookService, RecursoNoDisponible,
    id_de_notebook
)

logger = logging.getLogger(__name__)

router = APIRouter()
notebook_service = NotebookService()


class NotebookCrearRequest(BaseModel):
    nombre: str


class NotebookRenombrarRequest(BaseModel):
    nombre: str  # sin `max_length`: el largo lo valida el servicio, para dar su mensaje (RF-17.82)


class NotebookEliminadoRespuesta(BaseModel):
    mensaje: str
    id: int


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
    except NombreNoValido as e:
        # Una regla del nombre: su mensaje es para el usuario (RF-17.81-17.85, 17.93) y el rechazo queda en la bitácora (RF-21.81).
        await notebooks_audit_service.registrar_creacion_fallida(db, current_user["user_id"], e.motivo, "validacion")
        raise HTTPException(status_code=400, detail=e.mensaje)
    except Exception as e:
        # Sin el texto de la excepción ni en la respuesta ni en el registro: puede traer rutas internas o lo escrito por el
        # usuario (RF-17.30). El registro conserva el tipo del error y su traza para diagnosticarlo.
        logger.error(
            "Error creando el notebook (%s)\n%s", type(e).__name__, "".join(traceback.format_tb(e.__traceback__))
        )
        await notebooks_audit_service.registrar_creacion_fallida(db, current_user["user_id"], "error inesperado", "interno")
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


def _clave_validada(notebook_id: str) -> Optional[str]:
    """La clave `NB-<id>` si el id de la URL es canónico; si no, None: el texto libre de la URL no llega a la bitácora."""
    id_notebook = id_de_notebook(notebook_id)
    return f"NB-{id_notebook}" if id_notebook is not None else None


def _error_inesperado(e: Exception, accion: str) -> HTTPException:
    """El 500 genérico: la traza va al registro del servidor sin el texto de la excepción (RF-17.30, RF-17.90)."""
    logger.error("Error al %s un notebook (%s)\n%s", accion, type(e).__name__, "".join(traceback.format_tb(e.__traceback__)))
    return HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/{notebook_id}", response_model=NotebookResponse)
async def renombrar_notebook(
    notebook_id: str,
    request: NotebookRenombrarRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Renombra un notebook propio. El id llega como texto y solo vale el canónico: `abc`, `05` o `+5` dan 404, no 422."""
    usuario = current_user["user_id"]
    try:
        # El servicio resuelve primero el notebook (404 uniforme) y después valida el nombre (RNF-07.80).
        notebook, cambiado = await notebook_service.renombrar_notebook(db, notebook_id, request.nombre, usuario)
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user, no_disponible, TiposAccion.RENOMBRAR_NOTEBOOK)
    except NombreNoValido as e:
        # Aquí el id ya es canónico: el servicio lo resolvió antes de validar el nombre.
        await notebooks_audit_service.registrar_renombrado(
            db, usuario, f"NB-{notebook_id}", exito=False, motivo=e.motivo, tipo_error="validacion")
        raise HTTPException(status_code=400, detail=e.mensaje)
    except Exception as e:
        await notebooks_audit_service.registrar_renombrado(
            db, usuario, _clave_validada(notebook_id), exito=False, motivo="error inesperado", tipo_error="interno")
        raise _error_inesperado(e, "renombrar")

    if cambiado:  # el mismo nombre responde 200 sin dejar fila (RF-17.83)
        await notebooks_audit_service.registrar_renombrado(db, usuario, notebook.clave_interna, exito=True)
    return _to_response(notebook)


@router.delete("/{notebook_id}", response_model=NotebookEliminadoRespuesta)
async def eliminar_notebook(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Elimina de forma lógica un notebook propio: deja de estar disponible, pero no se borra nada (RN-01)."""
    usuario = current_user["user_id"]
    try:
        notebook = await notebook_service.eliminar_notebook(db, notebook_id, usuario)
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user, no_disponible, TiposAccion.ELIMINAR_NOTEBOOK)
    except Exception as e:
        await notebooks_audit_service.registrar_eliminacion(
            db, usuario, _clave_validada(notebook_id), exito=False, motivo="error inesperado", tipo_error="interno")
        raise _error_inesperado(e, "eliminar")

    await notebooks_audit_service.registrar_eliminacion(db, usuario, notebook.clave_interna, exito=True)
    return NotebookEliminadoRespuesta(mensaje="Notebook eliminado", id=notebook.CN_Id_notebook)


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
