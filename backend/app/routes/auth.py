from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth_schemas import LoginRequest, LoginResponse, CambiarContrasenaRequest

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=LoginResponse)
async def login_usuario(
    login_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    """Autentica un usuario y devuelve información del usuario"""
    try:
        usuario_autenticado = await auth_service.autenticar_usuario(
            db, login_data.email, login_data.password
        )
        
        if not usuario_autenticado:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        return usuario_autenticado
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.put("/cambiar-contrasenna")
async def cambiar_contrasenna(
    cambio_data: CambiarContrasenaRequest,
    db: Session = Depends(get_db)
):
    """Cambia la contraseña de un usuario"""
    try:
        resultado = await auth_service.cambiar_contrasenna(
            db, 
            cambio_data.cedula_usuario,
            cambio_data.contrasenna_actual, 
            cambio_data.nueva_contrasenna
        )
        
        if not resultado:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error al cambiar la contraseña"
            )
        
        return {"success": True, "message": "Contraseña cambiada exitosamente"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error en cambiar contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )
