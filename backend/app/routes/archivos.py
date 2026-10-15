"""
Rutas de Gestión y Descarga de Archivos de Expedientes Judiciales.

Este módulo define endpoints REST para listar y descargar archivos asociados a
expedientes judiciales. Todos los accesos a archivos se auditan en la bitácora.

Funcionalidades principales:
    - Listado de archivos por expediente
    - Descarga de archivos específicos
    - Validación de estado de procesamiento
    - Auditoría completa de accesos

Arquitectura de archivos:
    - Almacenamiento: uploads/{expediente_numero}/{archivo}
    - Control de acceso: require_usuario_judicial (usuarios judiciales y admins)
    - Validación: Solo archivos procesados pueden descargarse
    - Auditoría: Todos los listados y descargas se registran

Validaciones de seguridad:
    - Formato de expediente validado (regex)
    - Estado de procesamiento verificado en BD
    - Existencia de archivo en disco verificada
    - Path traversal prevenido mediante validación

Endpoints principales:
    - GET /archivos/expediente/{numero}/archivos: Listar archivos del expediente
    - GET /archivos/expediente/{numero}/archivo/{nombre}: Descargar archivo específico
    - GET /archivos/download?ruta_archivo={ruta}: Descargar por ruta completa

Example:
    ```python
    # Listar archivos de un expediente
    response = await client.get(
        "/archivos/expediente/00-000123-0456-PE/archivos",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print(f"Total archivos: {response['total_archivos']}")
    for archivo in response['archivos']:
        print(f"- {archivo['nombre_archivo']} ({archivo['estado_procesamiento']})")
    
    # Descargar archivo específico
    file_content = await client.get(
        "/archivos/expediente/00-000123-0456-PE/archivo/demanda.pdf",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    # El navegador recibe FileResponse con Content-Disposition attachment
    
    # Descargar por ruta (migrado desde /documentos/file)
    file_content = await client.get(
        "/archivos/download?ruta_archivo=uploads/00-000123-0456-PE/sentencia.pdf",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    ```

Formato de expediente:
    Formato esperado: XX-XXXXXX-XXXX-YY
    Ejemplo: 00-000123-0456-PE
    - XX: Código de tipo (00-99)
    - XXXXXX: Número secuencial (6-8 dígitos)
    - XXXX: Año (4-6 dígitos)
    - YY: Tipo de proceso (opciona, 1-2 letras)

Estados de procesamiento:
    - 1: PENDIENTE - En cola para procesar
    - 2: EN_PROCESO - Actualmente procesándose
    - 3: COMPLETADO - Procesado exitosamente, listo para descarga
    - 4: ERROR - Error en procesamiento

Note:
    Solo archivos con estado COMPLETADO (3) pueden descargarse.
    Intentos de descarga de archivos no procesados retornan HTTP 404 (el mismo que un archivo inexistente).

See Also:
    - app.services.documentos.file_management_service: Gestión de archivos
    - app.utils.expediente_validator: Validación de formato de expediente
    - app.repositories.documento_repository: Acceso a BD de documentos
    - app.services.bitacora.archivos_audit_service: Auditoría de acceso a archivos
"""
from fastapi import APIRouter, HTTPException, Depends, Path as PathParam
from typing import List, Optional
from sqlalchemy.orm import Session
import logging
import os

from app.services.documentos.file_management_service import (
    file_management_service, AccesoArchivoDenegado, _sin_control
)
from app.db.database import get_db
from app.utils.expediente_validator import validar_expediente
from app.auth.jwt_auth import require_usuario_judicial
from app.services.bitacora.archivos_audit_service import archivos_audit_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def _auditar_rechazo(db: Session, current_user, rechazo: AccesoArchivoDenegado) -> None:
    """Registra una descarga rechazada solo con su motivo (RF-21.20, RNF-07.24); si el registro falla, la respuesta no cambia."""
    await archivos_audit_service.registrar_descarga_rechazada(
        db=db, usuario_id=current_user["user_id"], motivo=rechazo.motivo
    )


async def _auditar_error_interno(db: Session, current_user) -> None:
    """Registra un error inesperado de descarga como error interno, sin el nombre ni la ruta pedidos (RNF-07.24)."""
    await archivos_audit_service.registrar_descarga_archivo(
        db=db, usuario_id=current_user["user_id"], nombre_archivo=None, exito=False, error="error interno"
    )

@router.get("/expediente/{expediente_numero}/archivos")
async def listar_archivos_expediente(
    expediente_numero: str = PathParam(..., description="Número del expediente"),
    db: Session = Depends(get_db),
    current_user=Depends(require_usuario_judicial)
):
    """
    Lista todos los archivos de un expediente específico.
    """
    # Validar formato del expediente
    if not validar_expediente(expediente_numero):
        raise HTTPException(
            status_code=400,
            detail="Formato de expediente inválido"
        )
    
    try:
        archivos = file_management_service.listar_archivos_expediente(expediente_numero, db)
        total_archivos = len(archivos)
        
        # Auditar listado de archivos
        await archivos_audit_service.registrar_listado_archivos(
            db=db,
            usuario_id=current_user["user_id"],
            expediente_numero=expediente_numero,
            total_archivos=total_archivos,
            exito=True
        )
        
        return {
            "expediente": expediente_numero,
            "total_archivos": total_archivos,
            "archivos": archivos
        }
    except Exception:
        # El texto de la excepción puede traer rutas del servidor o nombres de personas: solo va al registro del servidor
        # (RNF-07.23, RNF-07.24); la bitácora y la respuesta llevan un texto genérico.
        logger.exception("Error inesperado al listar los archivos de un tema")
        await archivos_audit_service.registrar_listado_archivos(
            db=db,
            usuario_id=current_user["user_id"],
            expediente_numero=expediente_numero,
            total_archivos=0,
            exito=False,
            error="error interno"
        )

        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/expediente/{expediente_numero}/archivo/{nombre_archivo}")
async def descargar_archivo_expediente(
    expediente_numero: str = PathParam(..., description="Número del expediente"),
    nombre_archivo: str = PathParam(..., description="Nombre del archivo"),
    db: Session = Depends(get_db),
    current_user=Depends(require_usuario_judicial)
):
    """
    Descarga un archivo específico de un expediente.
    """
    # Decodificar el nombre del archivo en caso de que contenga caracteres especiales
    from urllib.parse import unquote
    nombre_archivo = unquote(nombre_archivo)
    
    # Validar formato del expediente
    if not validar_expediente(expediente_numero):
        raise HTTPException(
            status_code=400,
            detail="Formato de expediente inválido"
        )
    
    try:
        # Misma comprobación que la descarga por ruta, sin lógica duplicada: documento registrado y Procesado, notebook
        # propio y archivo dentro de la carpeta de su tema; si no, AccesoArchivoDenegado (404 uniforme, RNF-07.20, RF-18.20).
        ruta_documento = f"uploads/{expediente_numero}/{nombre_archivo}"
        ubicacion = await file_management_service.obtener_documento_por_ruta(db, ruta_documento, current_user["user_id"])

        # Obtener tamaño del archivo para auditoría
        tamaño_bytes = None
        try:
            tamaño_bytes = os.path.getsize(ubicacion)
        except OSError:
            pass

        file_response = file_management_service.descargar_archivo(ubicacion)

        # Auditar descarga exitosa (con la ruta del documento, no la del servidor, y sin caracteres de control)
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=_sin_control(ubicacion.name),
            expediente_numero=_sin_control(expediente_numero),
            ruta_archivo=_sin_control(ruta_documento),
            tamaño_bytes=tamaño_bytes,
            exito=True
        )

        return file_response

    except AccesoArchivoDenegado as e:
        await _auditar_rechazo(db, current_user, e)
        raise
    except HTTPException:
        raise
    except Exception:
        await _auditar_error_interno(db, current_user)
        logger.exception("Error inesperado en la descarga por tema y nombre")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/download")
async def descargar_archivo_por_ruta(
    ruta_archivo: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_usuario_judicial)
):
    """
    Descarga un archivo específico usando su ruta completa.
    Funcionalidad migrada desde /documentos/file para centralizar descargas.
    
    Args:
        ruta_archivo: Ruta completa del archivo a descargar
    """
    try:
        # Se conserva la segunda decodificación (D9): la ruta que se comprueba es la final, ya decodificada.
        from urllib.parse import unquote
        ruta_archivo = unquote(ruta_archivo)

        # Solo se entrega un documento registrado, Procesado, propio y dentro de la carpeta de su tema; si no,
        # AccesoArchivoDenegado (404 uniforme) y no se completa ni se busca ninguna otra ruta (RNF-07.20, RF-18.20).
        ubicacion = await file_management_service.obtener_documento_por_ruta(db, ruta_archivo, current_user["user_id"])
        nombre_archivo = ubicacion.name

        # Obtener tamaño del archivo para auditoría
        tamaño_bytes = None
        try:
            tamaño_bytes = os.path.getsize(ubicacion)
        except OSError:
            pass

        # Realizar descarga
        file_response = file_management_service.descargar_archivo(ubicacion)

        # Auditar descarga exitosa (con la ruta del documento, no la del servidor)
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=_sin_control(nombre_archivo),
            ruta_archivo=_sin_control(ruta_archivo),
            tamaño_bytes=tamaño_bytes,
            exito=True
        )

        return file_response

    except AccesoArchivoDenegado as e:
        await _auditar_rechazo(db, current_user, e)
        raise
    except HTTPException:
        # Re-lanzar excepciones HTTP (el 400 de archivo vacío)
        raise
    except Exception:
        # El detalle va solo al registro del servidor; ni la respuesta ni la bitácora llevan la ruta pedida (RNF-07.23, RNF-07.24)
        await _auditar_error_interno(db, current_user)
        logger.exception("Error inesperado en la descarga por ruta")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
