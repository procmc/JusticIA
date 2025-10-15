from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from app.db.database import get_db
from app.services.auth_service import AuthService
from app.services.bitacora.auth_audit_service import auth_audit_service

logger = logging.getLogger(__name__)
from app.schemas.auth_schemas import (
    LoginRequest, LoginResponse, CambiarContrasenaRequest,
    SolicitarRecuperacionRequest, SolicitarRecuperacionResponse,
    VerificarCodigoRequest, VerificarCodigoResponse,
    CambiarContrasenaRecuperacionRequest, RestablecerContrasenaRequest,
    RestablecerContrasenaResponse, MensajeExito
)

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
            # Registrar intento de login fallido
            await auth_audit_service.registrar_login_fallido(
                db=db,
                email=login_data.email,
                motivo="Credenciales inválidas"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Registrar login exitoso - usuario_autenticado.user contiene toda la info
        await auth_audit_service.registrar_login_exitoso(
            db=db,
            usuario_id=usuario_autenticado.user.id,  # Ya es string (cédula)
            email=usuario_autenticado.user.email,
            rol=usuario_autenticado.user.role
        )
        
        return usuario_autenticado
        
    except ValueError as e:
        # Registrar intento de login fallido por error de validación
        await auth_audit_service.registrar_login_fallido(
            db=db,
            email=login_data.email,
            motivo=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
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
        
        # Registrar cambio de contraseña - cedula_usuario es el CN_Id_usuario (string)
        await auth_audit_service.registrar_cambio_password(
            db=db,
            usuario_id=cambio_data.cedula_usuario,
            tipo_cambio="cambio_usuario"
        )
        
        return {"success": True, "message": "Contraseña cambiada exitosamente"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/solicitar-recuperacion", response_model=SolicitarRecuperacionResponse)
async def solicitar_recuperacion_contrasenna(
    solicitud: SolicitarRecuperacionRequest,
    db: Session = Depends(get_db)
):
    """Solicita recuperación de contraseña enviando código por correo"""
    try:
        resultado = await auth_service.solicitar_recuperacion_contrasenna(
            db, solicitud.email
        )
        
        # Registrar solicitud de recuperación
        await auth_audit_service.registrar_solicitud_recuperacion(
            db=db,
            email=solicitud.email
        )
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en solicitar recuperación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/verificar-codigo", response_model=VerificarCodigoResponse)
async def verificar_codigo_recuperacion(
    verificacion: VerificarCodigoRequest,
    db: Session = Depends(get_db)
):
    """Verifica el código de recuperación enviado por correo"""
    email_from_token = None
    try:
        # Intentar extraer el email del token para auditoría
        import jwt
        import os
        jwt_secret = os.getenv("JWT_SECRET_KEY", "default-secret-key-change-in-production")
        try:
            decoded = jwt.decode(verificacion.token, jwt_secret, algorithms=["HS256"])
            email_from_token = decoded.get('email', 'desconocido')
        except:
            email_from_token = 'desconocido'
        
        resultado = await auth_service.verificar_codigo_recuperacion(
            db, verificacion.token, verificacion.codigo
        )
        
        # Registrar verificación exitosa
        await auth_audit_service.registrar_verificacion_codigo(
            db=db,
            email=email_from_token,
            exitoso=True
        )
        
        return resultado
        
    except ValueError as e:
        # Registrar verificación fallida
        await auth_audit_service.registrar_verificacion_codigo(
            db=db,
            email=email_from_token or 'desconocido',
            exitoso=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en verificar código: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/cambiar-contrasenna-recuperacion", response_model=MensajeExito)
async def cambiar_contrasenna_recuperacion(
    cambio: CambiarContrasenaRecuperacionRequest,
    db: Session = Depends(get_db)
):
    """Cambia la contraseña después de verificación exitosa del código"""
    try:
        resultado = await auth_service.cambiar_contrasenna_recuperacion(
            db, cambio.verificationToken, cambio.nuevaContrasenna
        )

        return resultado
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en cambiar contraseña recuperación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/restablecer-contrasenna", response_model=RestablecerContrasenaResponse)
async def restablecer_contrasenna(
    restablecimiento: RestablecerContrasenaRequest,
    db: Session = Depends(get_db)
):
    """Restablece la contraseña de un usuario (función para administradores)"""
    try:
        resultado = await auth_service.restablecer_contrasenna(
            db, restablecimiento.cedula
        )
        
        # Registrar restablecimiento - cedula es el CN_Id_usuario (string)
        await auth_audit_service.registrar_cambio_password(
            db=db,
            usuario_id=restablecimiento.cedula,
            tipo_cambio="restablecimiento_admin"
        )
        
        return resultado
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error en restablecer contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )
