"""
Rutas REST del Estudio del notebook (spec 010).

Endpoints (todos bajo /estudio, para el notebook propio del Usuario Gubernamental):
    - POST /estudio/{id}/generar: Genera un resumen, un informe o un mapa mental con las fuentes marcadas (transmite eventos
      `progreso`, `resultado` o `error` y `done`; cerrar la conexión cancela la generación y no guarda nada)
    - GET /estudio/{id}/resultados: Lista los resultados guardados del notebook, el más reciente primero
    - GET /estudio/{id}/resultados/{id}: Abre un resultado con su contenido
    - POST /estudio/{id}/notas: Guarda una respuesta del chat como nota
    - DELETE /estudio/{id}/resultados/{id}: Quita un resultado de la lista (baja lógica, RN-01)

Las rutas solo reciben, llaman al servicio, registran en la bitácora y traducen los errores. Un notebook o un resultado ajeno o
inexistente da el mismo 404 y deja un intento fallido solo con su motivo (RNF-07.120, RF-21.122).

Ver también:
    * app.services.estudio_service: Lógica de negocio
    * app.services.bitacora.notebooks_audit_service: Registro en la bitácora (RF-21.120, RF-21.121)
"""
import json
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.jwt_auth import require_usuario_judicial
from app.constants.tipos_accion import TiposAccion
from app.db.database import SessionLocal, get_db
from app.schemas.estudio_schemas import (
    GenerarRequest, MensajeResultado, NotaCrearRequest, ResultadoDetalle, ResultadoResumen
)
from app.services.bitacora.notebooks_audit_service import (
    MOTIVO_NOTEBOOK_NO_DISPONIBLE, notebooks_audit_service
)
from app.services.estudio_service import (
    MENSAJE_DEMASIADO_EXTENSAS, MENSAJE_EN_CURSO, MENSAJE_SIN_FUENTES, FuentesDemasiadoExtensas, GeneracionEnCurso,
    estudio_service,
)
from app.services.notebook_service import RecursoNoDisponible, SeleccionVacia, id_de_notebook

logger = logging.getLogger(__name__)

router = APIRouter()


def _clave_validada(notebook_id: str):
    """La clave `NB-<id>` si el id de la URL es canónico; si no, None: el texto libre de la URL no llega a la bitácora."""
    id_notebook = id_de_notebook(notebook_id)
    return f"NB-{id_notebook}" if id_notebook is not None else None


async def _no_encontrado(db: Session, usuario_id: str, no_disponible: RecursoNoDisponible, tipo_accion_id: int) -> HTTPException:
    """Deja el intento fallido solo con su motivo (RF-21.122) y devuelve el 404 uniforme (RNF-07.120)."""
    await notebooks_audit_service.registrar_intento_fallido(
        db=db, usuario_id=usuario_id, tipo_accion_id=tipo_accion_id, motivo=no_disponible.motivo)
    if no_disponible.motivo == MOTIVO_NOTEBOOK_NO_DISPONIBLE:
        return HTTPException(status_code=404, detail="Notebook no encontrado")
    return HTTPException(status_code=404, detail="Resultado no encontrado en este notebook")


def _error_inesperado(e: Exception, accion: str) -> HTTPException:
    """El 500 genérico: la traza va al registro del servidor sin el texto de la excepción."""
    logger.error("Error al %s en el Estudio (%s)\n%s", accion, type(e).__name__, "".join(traceback.format_tb(e.__traceback__)))
    return HTTPException(status_code=500, detail="Error interno del servidor")


def _evento(datos: dict) -> str:
    return f"data: {json.dumps(datos, ensure_ascii=False)}\n\n"


@router.post("/{notebook_id}/generar")
async def generar_resultado(
    notebook_id: str,
    request: GenerarRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Genera un resultado de estudio con las fuentes marcadas y lo transmite como eventos (RF-11.120 a RF-11.132)."""
    usuario = current_user["user_id"]
    clave = _clave_validada(notebook_id)
    try:
        preparacion = await estudio_service.preparar_generacion(db, notebook_id, request.tipo, request.documentos, usuario)
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, usuario, no_disponible, TiposAccion.GENERAR_RESULTADO_ESTUDIO)
    except SeleccionVacia:
        raise HTTPException(status_code=400, detail=MENSAJE_SIN_FUENTES)  # sin llamar al modelo ni guardar nada (RF-11.121)
    except GeneracionEnCurso:
        raise HTTPException(status_code=409, detail=MENSAJE_EN_CURSO)
    except FuentesDemasiadoExtensas:
        await notebooks_audit_service.registrar_generacion(
            db, usuario, clave, request.tipo, exito=False, motivo="fuentes demasiado extensas", tipo_error="validacion")
        raise HTTPException(status_code=400, detail=MENSAJE_DEMASIADO_EXTENSAS)
    except Exception as e:
        await notebooks_audit_service.registrar_generacion(
            db, usuario, clave, request.tipo, exito=False, motivo="error inesperado", tipo_error="interno")
        raise _error_inesperado(e, "generar")

    motivos = {"tiempo": "tiempo agotado", "salida_invalida": "salida inválida", "motor": "motor no disponible",
               "interno": "error inesperado"}

    async def eventos():
        async for evento in estudio_service.ejecutar(preparacion):
            if evento["type"] in ("resultado", "error"):
                # La sesión de la petición ya se cerró al empezar el envío: se abre una propia para la bitácora.
                with SessionLocal() as db_bitacora:
                    if evento["type"] == "resultado":
                        await notebooks_audit_service.registrar_generacion(
                            db_bitacora, usuario, preparacion.clave, preparacion.tipo, exito=True,
                            resultado_id=evento["resultado"]["id"], fuentes=len(preparacion.fuentes))
                    else:
                        await notebooks_audit_service.registrar_generacion(
                            db_bitacora, usuario, preparacion.clave, preparacion.tipo, exito=False,
                            motivo=motivos.get(evento["codigo"], "error inesperado"),
                            tipo_error="validacion" if evento["codigo"] == "salida_invalida" else "interno")
            yield _evento(evento)

    return StreamingResponse(
        eventos(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/{notebook_id}/resultados", response_model=list[ResultadoResumen])
async def listar_resultados(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Lista los resultados guardados del notebook, del más reciente al más antiguo (RF-17.121)."""
    try:
        return await estudio_service.listar_resultados(db, notebook_id, current_user["user_id"])
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user["user_id"], no_disponible, TiposAccion.LISTAR_ARCHIVOS)


@router.get("/{notebook_id}/resultados/{resultado_id}", response_model=ResultadoDetalle)
async def abrir_resultado(
    notebook_id: str,
    resultado_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Abre un resultado guardado con su contenido, sin llamar al modelo (RF-14.121). Abrirlo no se registra."""
    try:
        return await estudio_service.obtener_resultado(db, notebook_id, resultado_id, current_user["user_id"])
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, current_user["user_id"], no_disponible, TiposAccion.LISTAR_ARCHIVOS)


@router.post("/{notebook_id}/notas", response_model=ResultadoDetalle)
async def guardar_nota(
    notebook_id: str,
    request: NotaCrearRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Guarda una respuesta del chat como nota, con su pregunta y sus citas (RF-14.127). No llama al modelo."""
    usuario = current_user["user_id"]
    try:
        resultado = await estudio_service.guardar_nota(
            db, notebook_id, usuario, request.pregunta, request.respuesta, request.fuentes)
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, usuario, no_disponible, TiposAccion.GUARDAR_NOTA)
    except ValueError as e:
        await notebooks_audit_service.registrar_nota(
            db, usuario, _clave_validada(notebook_id), None, exito=False, motivo="respuesta vacía", tipo_error="validacion")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await notebooks_audit_service.registrar_nota(
            db, usuario, _clave_validada(notebook_id), None, exito=False, motivo="error inesperado", tipo_error="interno")
        raise _error_inesperado(e, "guardar una nota")

    await notebooks_audit_service.registrar_nota(db, usuario, _clave_validada(notebook_id), resultado.CN_Id_resultado, exito=True)
    return estudio_service.describir(resultado, con_contenido=True)


@router.delete("/{notebook_id}/resultados/{resultado_id}", response_model=MensajeResultado)
async def quitar_resultado(
    notebook_id: str,
    resultado_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial),
):
    """Quita un resultado de la lista con una baja lógica: la fila se conserva (RF-14.124, RN-01.120)."""
    usuario = current_user["user_id"]
    try:
        notebook, resultado = await estudio_service.quitar_resultado(db, notebook_id, resultado_id, usuario)
    except RecursoNoDisponible as no_disponible:
        raise await _no_encontrado(db, usuario, no_disponible, TiposAccion.QUITAR_RESULTADO_ESTUDIO)
    except Exception as e:
        await notebooks_audit_service.registrar_quitar_resultado(
            db, usuario, _clave_validada(notebook_id), id_de_notebook(resultado_id), exito=False, motivo="error inesperado",
            tipo_error="interno")
        raise _error_inesperado(e, "quitar un resultado")

    await notebooks_audit_service.registrar_quitar_resultado(db, usuario, notebook.clave_interna, resultado.CN_Id_resultado, exito=True)
    return MensajeResultado(mensaje="Resultado quitado", id=resultado.CN_Id_resultado)
