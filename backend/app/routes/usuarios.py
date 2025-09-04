from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.services.usuario_service import UsuarioService
from app.schemas.usuario_schemas import UsuarioRespuesta, UsuarioCrear, UsuarioEditar, MensajeRespuesta

router = APIRouter()
usuario_service = UsuarioService()

@router.get("/", response_model=List[UsuarioRespuesta])
def obtener_usuarios(db: Session = Depends(get_db)):
    """Obtiene todos los usuarios"""
    usuarios = usuario_service.obtener_todos_usuarios(db)
    return usuarios

@router.get("/{usuario_id}", response_model=UsuarioRespuesta)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtiene un usuario por ID"""
    usuario = usuario_service.obtener_usuario(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

@router.post("/", response_model=UsuarioRespuesta)
async def crear_usuario(usuario_data: UsuarioCrear, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario con contraseña automática.
    SIEMPRE genera contraseña aleatoria y envía correo al usuario.
    Similar a Node.js con nodemailer para envío automático.
    """
    try:
        usuario = await usuario_service.crear_usuario(
            db, usuario_data.nombre_usuario, usuario_data.correo, 
            usuario_data.id_rol  # Sin contraseña - se genera automáticamente
        )
        if not usuario:
            raise HTTPException(status_code=500, detail="Error al crear usuario")
        return usuario
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error en crear_usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/{usuario_id}", response_model=UsuarioRespuesta)
def editar_usuario(usuario_id: int, usuario_data: UsuarioEditar, db: Session = Depends(get_db)):
    """Edita un usuario incluyendo rol y estado"""
    usuario = usuario_service.editar_usuario(
        db, usuario_id, usuario_data.nombre_usuario, usuario_data.correo, 
        usuario_data.id_rol, usuario_data.id_estado
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario
