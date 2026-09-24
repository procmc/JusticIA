"""
Rutas REST para Notebooks (NotebookServIA).

Endpoints:
    - POST /notebooks: Crear un notebook nuevo
    - GET /notebooks: Listar los notebooks del usuario autenticado

Los documentos se suben a un notebook reutilizando el endpoint ya
existente POST /ingesta/archivos, pasando la clave_interna del
notebook (ej. "NB-7") como CT_Num_expediente — ver
app.db.models.notebook.T_Notebook.clave_interna.

Ver también:
    * app.services.notebook_service: Lógica de negocio
    * app.routes.ingesta: Reutilizado para subir documentos a un notebook
    * app.routes.rag: Chat acotado a un notebook (notebook_id)

Authors:
    ServIA Team

Version:
    1.0.0
"""

import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.auth.jwt_auth import require_usuario_judicial
from app.services.notebook_service import NotebookService
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.documento_repository import DocumentoRepository
from app.services.documentos.file_management_service import file_management_service
from app.vectorstore import get_vectorstore_backend

router = APIRouter()
notebook_service = NotebookService()
expediente_repo = ExpedienteRepository()
documento_repo = DocumentoRepository()


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
        return _to_response(notebook)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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


async def _obtener_notebook_o_404(db: Session, notebook_id: int, usuario_id: str):
    notebook = await notebook_service.obtener_notebook_de_usuario(db, notebook_id, usuario_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook no encontrado")
    return notebook


def _obtener_documento_del_notebook_o_404(db: Session, notebook, documento_id: int):
    documento = documento_repo.obtener_por_id(db, documento_id)
    if not documento or notebook.clave_interna not in [e.CT_Num_expediente for e in documento.expedientes]:
        raise HTTPException(status_code=404, detail="Documento no encontrado en este notebook")
    return documento


@router.get("/{notebook_id}/documentos", response_model=list[DocumentoNotebookResponse])
async def listar_documentos_notebook(
    notebook_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Lista los documentos ya subidos y procesados de un notebook."""
    notebook = await _obtener_notebook_o_404(db, notebook_id, current_user["user_id"])

    expediente = expediente_repo.obtener_por_numero(db, notebook.clave_interna)
    if not expediente:
        return []

    documentos = documento_repo.listar_por_expediente(db, expediente)
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
    notebook = await _obtener_notebook_o_404(db, notebook_id, current_user["user_id"])
    documento = _obtener_documento_del_notebook_o_404(db, notebook, documento_id)

    if not documento_repo.verificar_esta_procesado(db, notebook.clave_interna, documento.CT_Nombre_archivo):
        raise HTTPException(status_code=400, detail="El archivo aún no está disponible para previsualizar")

    ruta_archivo = file_management_service.obtener_ruta_archivo(notebook.clave_interna, documento.CT_Nombre_archivo)
    if not ruta_archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

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
    notebook = await _obtener_notebook_o_404(db, notebook_id, current_user["user_id"])
    documento = _obtener_documento_del_notebook_o_404(db, notebook, documento_id)

    # 1. Chunks de Qdrant
    await get_vectorstore_backend().delete_document_chunks(documento_id)

    # 2. Archivo físico en disco
    ruta = file_management_service.obtener_ruta_archivo(notebook.clave_interna, documento.CT_Nombre_archivo)
    if ruta:
        try:
            ruta.unlink()
        except OSError:
            pass  # No bloquea el borrado del registro si el archivo ya no está

    # 3. Registro en base de datos (y la fila de la tabla de unión)
    documento_repo.eliminar(db, documento)

    return {"message": "Documento eliminado", "documento_id": documento_id}
