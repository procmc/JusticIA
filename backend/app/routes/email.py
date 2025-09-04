"""
Rutas para funcionalidades de correo electrónico
Funciones para probar y gestionar envío de correos
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
