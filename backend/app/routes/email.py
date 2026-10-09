"""
Rutas de Testing y Diagnóstico del Servicio de Correo Electrónico.

Este módulo define endpoints auxiliares para probar y verificar la configuración
del servicio de envío de correos electrónicos del sistema ServIA.

Endpoints de utilidad:
    - POST /email/test-email: Envía correo de prueba para validar configuración
    - GET /email/email-config: Obtiene configuración actual (sin credenciales sensibles)

Uso típico:
    Estos endpoints se utilizan durante la configuración inicial del sistema
    o para diagnóstico de problemas de envío de correos. No son parte
    del flujo normal de la aplicación.

Configuración requerida (variables de entorno):
    - EMAIL_PROVIDER: Proveedor de correo (gmail, outlook, smtp)
    - EMAIL_USERNAME: Cuenta de correo de envío
    - EMAIL_PASSWORD: Contraseña o app password
    - EMAIL_HOST: Servidor SMTP (opcional, se usa default según provider)
    - EMAIL_PORT: Puerto SMTP (default: 587)

Example:
    ```python
    # Probar configuración de correo (con el token de un Administrador)
    cabeceras = {"Authorization": f"Bearer {token_admin}"}
    response = await client.post("/email/test-email", headers=cabeceras, json={
        "email": "destino@example.com",
        "password": "password123",
        "nombre_usuario": "Usuario Test"
    })
    
    # Verificar configuración actual
    config = await client.get("/email/email-config", headers=cabeceras)
    print(config["provider"])  # gmail
    print(config["configured"])  # True si está configurado
    ```

Roles:
    Ambos endpoints exigen sesión de Administrador (require_administrador): sin token responden 401 y con
    un Usuario Gubernamental, 403. Ninguno devuelve al navegador el texto de una excepción ni la contraseña
    de la cuenta de correo (spec 003a, RNF-07.2).

See Also:
    - app.email.EmailService: Servicio de envío de correos
    - app.email.get_email_config_from_env: Carga de configuración desde .env
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from dotenv import load_dotenv
from app.auth.jwt_auth import require_administrador
from app.email import EmailService, get_email_config_from_env
from app.schemas.email_schemas import (
    ConfiguracionCorreoRespuesta, PruebaCorreoRespuesta, PruebaCorreoSolicitud
)

logger = logging.getLogger(__name__)

# Cargar variables de entorno (como en Node.js)
load_dotenv()

router = APIRouter()

@router.post("/test-email", response_model=PruebaCorreoRespuesta)
async def test_email(
    request: PruebaCorreoSolicitud,
    current_user: dict = Depends(require_administrador)
):
    """
    Prueba el envío de correo electrónico (solo Administrador).
    Si el servidor de correo no acepta el mensaje, responde 200 con success=False.
    """
    try:
        # Inicializar servicio de correo
        email_config = get_email_config_from_env()
        email_service = EmailService(email_config)
        
        # Enviar correo de prueba
        success = await email_service.send_password_email(
            to=request.email,
            password=request.password,
            usuario_nombre=request.nombre_usuario
        )
        
        if success:
            return PruebaCorreoRespuesta(
                success=True,
                message=f"Correo enviado exitosamente a {request.email}"
            )
        else:
            return PruebaCorreoRespuesta(
                success=False,
                message="Error al enviar el correo"
            )
            
    except Exception:
        # El detalle de la excepción puede traer datos del servidor de correo: va al registro, no al navegador
        logger.exception("Error en el envío de correo de prueba")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/email-config", response_model=ConfiguracionCorreoRespuesta)
async def get_email_config(current_user: dict = Depends(require_administrador)):
    """
    Obtiene la configuración actual de correo, sin credenciales (solo Administrador).
    Útil para verificar la configuración
    """
    try:
        return ConfiguracionCorreoRespuesta(
            provider=os.getenv("EMAIL_PROVIDER", "gmail"),
            username=os.getenv("EMAIL_USERNAME", "No configurado"),
            host=os.getenv("EMAIL_HOST", "Usando configuración por defecto"),
            port=os.getenv("EMAIL_PORT", "587"),
            configured=bool(os.getenv("EMAIL_USERNAME") and os.getenv("EMAIL_PASSWORD"))
        )
        
    except Exception:
        logger.exception("Error al obtener la configuración de correo")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )
