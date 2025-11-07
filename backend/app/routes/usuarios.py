from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.services.usuario_service import UsuarioService
from app.services.avatar_service import avatar_service
from app.schemas.usuario_schemas import UsuarioRespuesta, UsuarioCrear, UsuarioEditar, MensajeRespuesta, ActualizarAvatarRequest
from app.auth.jwt_auth import require_administrador, require_usuario_judicial
from app.services.bitacora.usuarios_audit_service import usuarios_audit_service

router = APIRouter()
usuario_service = UsuarioService()

@router.get("/", response_model=List[UsuarioRespuesta])
async def obtener_usuarios(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """Obtiene todos los usuarios - Solo administradores"""
    # obtener_todos_usuarios es un método síncrono
    usuarios = usuario_service.obtener_todos_usuarios(db)
    
    # Registrar consulta en bitácora (async)
    await usuarios_audit_service.registrar_consulta_usuarios(
        db=db,
        usuario_admin_id=current_user["user_id"]
    )
    
    return usuarios

@router.get("/{usuario_id}", response_model=UsuarioRespuesta)
async def obtener_usuario(
    usuario_id: str, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """Obtiene un usuario por ID (cédula) - Solo administradores"""
    # obtener_usuario es un método síncrono
    usuario = usuario_service.obtener_usuario(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Registrar consulta en bitácora (async)
    await usuarios_audit_service.registrar_consulta_usuario_especifico(
        db=db,
        usuario_admin_id=current_user["user_id"],
        usuario_consultado_id=usuario_id
    )
    
    return usuario

@router.post("/", response_model=UsuarioRespuesta)
async def crear_usuario(
    usuario_data: UsuarioCrear, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Crea un nuevo usuario con contraseña automática.
    SIEMPRE genera contraseña aleatoria y envía correo al usuario.
    Solo para administradores.
    """
    try:
        usuario = await usuario_service.crear_usuario(
            db, usuario_data.cedula, usuario_data.nombre_usuario, 
            usuario_data.nombre, usuario_data.apellido_uno, usuario_data.apellido_dos,
            usuario_data.correo, usuario_data.id_rol  # Sin contraseña - se genera automáticamente
        )
        if not usuario:
            raise HTTPException(status_code=500, detail="Error al crear usuario")
        
        # Registrar creación en bitácora
        await usuarios_audit_service.registrar_creacion_usuario(
            db=db,
            usuario_admin_id=current_user["user_id"],
            usuario_creado_cedula=usuario_data.cedula,
            datos_usuario={
                "nombre_usuario": usuario_data.nombre_usuario,
                "nombre_completo": f"{usuario_data.nombre} {usuario_data.apellido_uno} {usuario_data.apellido_dos or ''}".strip(),
                "correo": usuario_data.correo,
                "id_rol": usuario_data.id_rol
            }
        )
        
        return usuario
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error en crear_usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{usuario_id}", response_model=UsuarioRespuesta)
async def editar_usuario(
    usuario_id: str, 
    usuario_data: UsuarioEditar, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """Edita un usuario incluyendo rol y estado - Solo administradores"""
    # editar_usuario es un método síncrono
    usuario = usuario_service.editar_usuario(
        db, usuario_id, usuario_data.nombre_usuario, usuario_data.nombre,
        usuario_data.apellido_uno, usuario_data.apellido_dos, usuario_data.correo, 
        usuario_data.id_rol, usuario_data.id_estado
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Registrar edición en bitácora (async)
    await usuarios_audit_service.registrar_edicion_usuario(
        db=db,
        usuario_admin_id=current_user["user_id"],
        usuario_editado_id=usuario_id,
        cambios={
            "nombre_usuario": usuario_data.nombre_usuario,
            "nombre": usuario_data.nombre,
            "apellido_uno": usuario_data.apellido_uno,
            "apellido_dos": usuario_data.apellido_dos,
            "correo": usuario_data.correo,
            "id_rol": usuario_data.id_rol,
            "id_estado": usuario_data.id_estado
        }
    )
    
    return usuario

@router.patch("/{usuario_id}/ultimo-acceso", response_model=UsuarioRespuesta)
async def actualizar_ultimo_acceso(
    usuario_id: str, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """Actualiza el último acceso del usuario - Solo administradores"""
    # actualizar_ultimo_acceso es un método síncrono
    usuario = usuario_service.actualizar_ultimo_acceso(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Registrar actualización en bitácora (async)
    await usuarios_audit_service.registrar_actualizacion_ultimo_acceso(
        db=db,
        usuario_admin_id=current_user["user_id"],
        usuario_actualizado_id=usuario_id
    )
    
    return usuario

@router.post("/{usuario_id}/resetear-contrasenna", response_model=MensajeRespuesta)
async def resetear_contrasenna(
    usuario_id: str, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_administrador)
):
    """
    Resetea la contraseña de un usuario y envía la nueva por correo.
    Solo para administradores.
    """
    try:
        usuario = await usuario_service.resetear_contrasenna_usuario(db, usuario_id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Registrar reseteo en bitácora
        await usuarios_audit_service.registrar_reseteo_contrasena(
            db=db,
            usuario_admin_id=current_user["user_id"],
            usuario_reseteado_id=usuario_id
        )
        
        return MensajeRespuesta(mensaje="Contraseña reseteada exitosamente. Se envió un correo con la nueva contraseña al usuario.")
        
    except Exception as e:
        print(f"Error al resetear contraseña: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/{usuario_id}/avatar/upload", response_model=MensajeRespuesta)
async def subir_avatar(
    usuario_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial)
):
    """Sube una imagen de avatar para un usuario"""
    # Validar permisos
    avatar_service.validar_permiso_usuario(current_user["user_id"], usuario_id)
    
    # Delegar toda la lógica al servicio
    resultado = await avatar_service.subir_avatar(usuario_id, file, db)
    
    return MensajeRespuesta(mensaje=resultado["mensaje"])


@router.put("/{usuario_id}/avatar/tipo", response_model=MensajeRespuesta)
async def actualizar_tipo_avatar(
    usuario_id: str,
    avatar_data: ActualizarAvatarRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial)
):
    """Actualiza la preferencia de avatar (sin subir imagen)"""
    # Validar permisos
    avatar_service.validar_permiso_usuario(current_user["user_id"], usuario_id)
    
    # Delegar toda la lógica al servicio
    resultado = await avatar_service.actualizar_tipo_avatar(usuario_id, avatar_data.avatar_tipo, db)
    
    return MensajeRespuesta(mensaje=resultado["mensaje"])


@router.delete("/{usuario_id}/avatar", response_model=MensajeRespuesta)
async def eliminar_avatar(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_usuario_judicial)
):
    """Elimina el avatar de un usuario"""
    # Validar permisos
    avatar_service.validar_permiso_usuario(current_user["user_id"], usuario_id)
    
    # Delegar toda la lógica al servicio
    resultado = await avatar_service.eliminar_avatar(usuario_id, db)
    
    return MensajeRespuesta(mensaje=resultado["mensaje"])

