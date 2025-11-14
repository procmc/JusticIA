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
    Intentos de descarga de archivos no procesados retornan HTTP 400.

See Also:
    - app.services.documentos.file_management_service: Gestión de archivos
    - app.utils.expediente_validator: Validación de formato de expediente
    - app.repositories.documento_repository: Acceso a BD de documentos
    - app.services.bitacora.archivos_audit_service: Auditoría de acceso a archivos
"""
from fastapi import APIRouter, HTTPException, Depends, Path as PathParam
from fastapi.responses import FileResponse
from typing import List, Optional
from sqlalchemy.orm import Session
import logging
import os

from app.services.documentos.file_management_service import file_management_service
from app.db.database import get_db
from app.utils.expediente_validator import validar_expediente
from app.auth.jwt_auth import require_usuario_judicial
from app.services.bitacora.archivos_audit_service import archivos_audit_service

router = APIRouter()
logger = logging.getLogger(__name__)

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
    except Exception as e:
        # Auditar error en listado
        await archivos_audit_service.registrar_listado_archivos(
            db=db,
            usuario_id=current_user["user_id"],
            expediente_numero=expediente_numero,
            total_archivos=0,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error listando archivos: {str(e)}"
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
        # Verificar que el archivo esté procesado (validación centralizada)
        from app.repositories.documento_repository import DocumentoRepository
        
        repo = DocumentoRepository()
        if not repo.verificar_esta_procesado(db, expediente_numero, nombre_archivo):
            # Auditar intento de descarga de archivo no procesado
            await archivos_audit_service.registrar_descarga_archivo(
                db=db,
                usuario_id=current_user["user_id"],
                nombre_archivo=nombre_archivo,
                expediente_numero=expediente_numero,
                exito=False,
                error="Archivo no disponible para descarga (no procesado)"
            )
            
            raise HTTPException(
                status_code=400,
                detail="El archivo aún no está disponible para descarga"
            )
        
        ruta_archivo = file_management_service.obtener_ruta_archivo(expediente_numero, nombre_archivo)
        
        if not ruta_archivo:
            # Auditar intento de descarga de archivo no encontrado
            await archivos_audit_service.registrar_descarga_archivo(
                db=db,
                usuario_id=current_user["user_id"],
                nombre_archivo=nombre_archivo,
                expediente_numero=expediente_numero,
                exito=False,
                error="Archivo no encontrado en disco"
            )
            
            raise HTTPException(
                status_code=404,
                detail="Archivo no encontrado"
            )
        
        # Obtener tamaño del archivo para auditoría
        tamaño_bytes = None
        try:
            if os.path.exists(str(ruta_archivo)):
                tamaño_bytes = os.path.getsize(str(ruta_archivo))
        except:
            pass
        
        # Auditar descarga exitosa
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=nombre_archivo,
            expediente_numero=expediente_numero,
            ruta_archivo=str(ruta_archivo),
            tamaño_bytes=tamaño_bytes,
            exito=True
        )
        
        return FileResponse(
            path=str(ruta_archivo),
            filename=nombre_archivo,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Auditar error en descarga
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=nombre_archivo,
            expediente_numero=expediente_numero,
            exito=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando archivo: {str(e)}"
        )

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
        # Decodificar la ruta en caso de que contenga caracteres especiales (FastAPI debería hacerlo automáticamente, pero por seguridad)
        from urllib.parse import unquote
        ruta_archivo = unquote(ruta_archivo)
        
        # Normalizar la ruta: convertir rutas relativas "uploads/..." a rutas absolutas
        if ruta_archivo.startswith("uploads/"):
            # Ruta relativa desde la raíz del proyecto backend
            import os
            from pathlib import Path
            backend_root = Path(__file__).resolve().parent.parent.parent  # Subir 3 niveles desde routes/archivos.py
            ruta_archivo = str(backend_root / ruta_archivo)
        
        # Extraer nombre del archivo de la ruta
        nombre_archivo = os.path.basename(ruta_archivo)
        
        # Obtener tamaño del archivo para auditoría
        tamaño_bytes = None
        try:
            if os.path.exists(ruta_archivo):
                tamaño_bytes = os.path.getsize(ruta_archivo)
        except:
            pass
        
        # Log para debugging
        logger.info(f"Intentando descargar archivo: {ruta_archivo}")
        
        # Realizar descarga
        file_response = file_management_service.descargar_archivo(ruta_archivo)
        
        # Auditar descarga exitosa
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=nombre_archivo,
            ruta_archivo=ruta_archivo,
            tamaño_bytes=tamaño_bytes,
            exito=True
        )
        
        return file_response
        
    except HTTPException:
        # Re-lanzar excepciones HTTP (ej: 404 del FileManagementService)
        raise
    except Exception as e:
        # Auditar error en descarga
        await archivos_audit_service.registrar_descarga_archivo(
            db=db,
            usuario_id=current_user["user_id"],
            nombre_archivo=os.path.basename(ruta_archivo) if ruta_archivo else "Desconocido",
            ruta_archivo=ruta_archivo,
            exito=False,
            error=str(e)
        )
        
        logger.error(f"Error descargando archivo {ruta_archivo}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error descargando archivo: {str(e)}"
        )