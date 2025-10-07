"""
Sistema de autenticación simple para JusticIA
"""

import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.rol import T_Rol
from app.config.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS
from app.constants.roles import ADMINISTRADOR, USUARIO_JUDICIAL


def create_token(user_id: int, role: str, username: Optional[str] = None) -> str:
    """Crea un token JWT simple"""
    payload = {
        "user_id": user_id,
        "role": role,
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifica un token JWT"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except:
        return None


def require_usuario_judicial(request: Request) -> Dict[str, Any]:
    """
    FastAPI Dependency para validar autenticación y rol Usuario Judicial.
    
    Uso:
        from fastapi import Depends
        from app.auth.jwt_auth import require_usuario_judicial
        
        @router.post("/ruta")
        async def mi_funcion(
            current_user: dict = Depends(require_usuario_judicial)
        ):
            # current_user contiene: {"user_id": int, "username": str, "role": str}
    """
    # Validar token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Token requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar rol
    token_role = payload.get("role")
    if token_role != USUARIO_JUDICIAL:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado"
        )
    
    # Verificar que el rol existe en BD
    db = next(get_db())
    try:
        rol_exists = db.query(T_Rol).filter(T_Rol.CT_Nombre_rol == USUARIO_JUDICIAL).first()
        if not rol_exists:
            raise HTTPException(
                status_code=500,
                detail=f"Error de configuración: Rol '{USUARIO_JUDICIAL}' no existe en la BD"
            )
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role")
        }
    finally:
        db.close()


def require_administrador(request: Request) -> Dict[str, Any]:
    """
    FastAPI Dependency para validar autenticación y rol Administrador.
    
    Uso:
        from fastapi import Depends
        from app.auth.jwt_auth import require_administrador
        
        @router.get("/admin/usuarios")
        async def listar_usuarios(
            current_user: dict = Depends(require_administrador)
        ):
            # current_user contiene: {"user_id": int, "username": str, "role": str}
    """
    # Validar token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Token requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar rol
    token_role = payload.get("role")
    if token_role != ADMINISTRADOR:
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado"
        )
    
    # Verificar que el rol existe en BD
    db = next(get_db())
    try:
        rol_exists = db.query(T_Rol).filter(T_Rol.CT_Nombre_rol == ADMINISTRADOR).first()
        if not rol_exists:
            raise HTTPException(
                status_code=500,
                detail=f"Error de configuración: Rol '{ADMINISTRADOR}' no existe en la BD"
            )
        
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "role": payload.get("role")
        }
    finally:
        db.close()


