"""
Sistema de autenticación simple para JusticIA
"""

import jwt
from functools import wraps
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.rol import T_Rol
from app.config.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS


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


def require_role(required_role_name: str):
    """
    Decorador que requiere un rol específico validando que exista en la BD.
    
    Uso: @require_role("Administrador")
         @require_role("Usuario_Judicial")
    
    Args:
        required_role_name: Nombre exacto del rol en la tabla T_Rol
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Buscar el objeto Request
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if hasattr(arg, 'headers') and hasattr(arg, 'method'):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(status_code=401, detail="Error interno: Request no encontrado")
            
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
            
            # Verificar que el rol del token coincida con el requerido
            token_role = payload.get("role")
            if token_role != required_role_name:
                raise HTTPException(
                    status_code=403,
                    detail=f"Acceso denegado"
                )
            
            # Verificar que el rol existe en la BD
            db = next(get_db())
            try:
                rol_exists = db.query(T_Rol).filter(T_Rol.CT_Nombre_rol == required_role_name).first()
                if not rol_exists:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error de configuración: Rol '{required_role_name}' no existe en la BD"
                    )
                
                # Si todo OK - inyectar datos del token
                kwargs['current_user'] = {
                    "user_id": payload.get("user_id"),
                    "username": payload.get("username"),
                    "role": payload.get("role")
                }
                
                return await func(*args, **kwargs)
                
            finally:
                db.close()
        
        return wrapper
    return decorator
