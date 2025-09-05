from fastapi import APIRouter, Depends, HTTPException, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.usuario import T_Usuario
from app.repositories.usuario_repository import UsuarioRepository

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/usuarios")
async def listar_usuarios_debug(db: Session = Depends(get_db)):
    """Endpoint temporal para debug - ver todos los usuarios"""
    usuarios = db.query(T_Usuario).all()
    resultado = []
    
    for usuario in usuarios:
        resultado.append({
            "id": usuario.CN_Id_usuario,
            "email": usuario.CT_Correo,
            "nombre_usuario": usuario.CT_Nombre_usuario,
            "nombre": f"{usuario.CT_Nombre} {usuario.CT_Apellido_uno}",
            "hash_password_preview": usuario.CT_Contrasenna[:50] + "...",
            "rol_id": usuario.CN_Id_rol,
            "estado_id": usuario.CN_Id_estado
        })
    
    return resultado

@router.post("/test-password")
async def test_password_debug(
    email: str, 
    password: str, 
    db: Session = Depends(get_db)
):
    """Endpoint temporal para debug - probar contraseña paso a paso"""
    repo = UsuarioRepository()
    
    # Paso 1: Buscar usuario por CT_Nombre_usuario
    usuario_por_nombre = db.query(T_Usuario).filter(T_Usuario.CT_Nombre_usuario == email).first()
    
    # Paso 2: Buscar usuario por CT_Correo
    usuario_por_correo = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
    
    resultado = {
        "email_buscado": email,
        "password_probado": password,
        "usuario_encontrado_por_nombre_usuario": usuario_por_nombre is not None,
        "usuario_encontrado_por_correo": usuario_por_correo is not None,
    }
    
    if usuario_por_nombre:
        resultado["datos_usuario_nombre"] = {
            "id": usuario_por_nombre.CN_Id_usuario,
            "email": usuario_por_nombre.CT_Correo,
            "nombre_usuario": usuario_por_nombre.CT_Nombre_usuario,
        }
        # Probar contraseña
        password_valida = repo.pwd_context.verify(password, usuario_por_nombre.CT_Contrasenna)
        resultado["password_valida_nombre_usuario"] = password_valida
    
    if usuario_por_correo:
        resultado["datos_usuario_correo"] = {
            "id": usuario_por_correo.CN_Id_usuario,
            "email": usuario_por_correo.CT_Correo,
            "nombre_usuario": usuario_por_correo.CT_Nombre_usuario,
        }
        # Probar contraseña
        password_valida = repo.pwd_context.verify(password, usuario_por_correo.CT_Contrasenna)
        resultado["password_valida_correo"] = password_valida
    
    return resultado

@router.post("/reset-password")
async def reset_password_debug(
    email: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Endpoint temporal para debug - resetear contraseña de un usuario"""
    repo = UsuarioRepository()
    
    # Buscar usuario por correo
    usuario = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Hashear nueva contraseña
    nueva_contrasenna_hash = repo._hash_password(new_password)
    
    # Actualizar contraseña
    usuario.CT_Contrasenna = nueva_contrasenna_hash
    db.commit()
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "email": email,
        "nueva_password": new_password,
        "usuario_id": usuario.CN_Id_usuario
    }
