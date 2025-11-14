"""
Rutas de Testing y Diagnóstico del Servicio de Correo Electrónico.

Este módulo define endpoints auxiliares para probar y verificar la configuración
del servicio de envío de correos electrónicos del sistema JusticIA.

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
    # Probar configuración de correo
    response = await client.post("/email/test-email", json={
        "email": "destino@example.com",
        "password": "password123",
        "nombre_usuario": "Usuario Test"
    })
    
    # Verificar configuración actual
    config = await client.get("/email/email-config")
    print(config["provider"])  # gmail
    print(config["configured"])  # True si está configurado
    ```

Note:
    Estos endpoints NO deberían estar expuestos en producción sin autenticación.
    Considerar agregar require_administrador en ambientes productivos.

See Also:
    - app.email.EmailService: Servicio de envío de correos
    - app.email.get_email_config_from_env: Carga de configuración desde .env
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from app.email import EmailService, get_email_config_from_env

# Cargar variables de entorno (como en Node.js)
load_dotenv()

router = APIRouter()

class TestEmailRequest(BaseModel):
    email: str
    password: str
    nombre_usuario: str = "Usuario de Prueba"

@router.post("/test-email")
async def test_email(request: TestEmailRequest):
    """
    Prueba el envío de correo electrónico
    Similar a una función de test en Node.js
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
            return {
                "success": True,
                "message": f"Correo enviado exitosamente a {request.email}"
            }
        else:
            return {
                "success": False,
                "message": "Error al enviar el correo"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar correo: {str(e)}"
        )

@router.get("/email-config")
async def get_email_config():
    """
    Obtiene la configuración actual de correo (sin credenciales)
    Útil para verificar la configuración
    """
    try:
        import os
        
        config_info = {
            "provider": os.getenv("EMAIL_PROVIDER", "gmail"),
            "username": os.getenv("EMAIL_USERNAME", "No configurado"),
            "host": os.getenv("EMAIL_HOST", "Usando configuración por defecto"),
            "port": os.getenv("EMAIL_PORT", "587"),
            "configured": bool(os.getenv("EMAIL_USERNAME") and os.getenv("EMAIL_PASSWORD"))
        }
        
        return config_info
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener configuración: {str(e)}"
        )
