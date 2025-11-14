"""
Configuración de Envío de Correos Electrónicos con Pydantic Settings.

Este módulo proporciona configuración centralizada para el servicio de email,
similar a Nodemailer en Node.js pero usando Pydantic para validación y carga desde .env.

Proveedores soportados:
    - Gmail: Requiere "App Password" (no contraseña normal)
    - Outlook/Hotmail: Autenticación SMTP estándar
    - Yahoo: Requiere configuración específica de seguridad
    - SMTP Genérico: Cualquier servidor SMTP custom

Variables de entorno requeridas (.env):
    ```env
    MAIL_USERNAME=tu-email@gmail.com
    MAIL_PASSWORD=tu-app-password-aqui
    MAIL_FROM=tu-email@gmail.com
    MAIL_FROM_NAME=JusticIA Sistema
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_STARTTLS=True
    ```

Configuración de Gmail:
    1. Habilitar verificación en 2 pasos en tu cuenta Google
    2. Generar "App Password" desde configuración de seguridad
    3. Usar el App Password (16 caracteres) en MAIL_PASSWORD
    4. No usar la contraseña normal de Gmail

Proveedores preconfigurados:
    EMAIL_PROVIDERS contiene configuraciones listas para usar:
        - gmail: smtp.gmail.com:587 con STARTTLS
        - outlook: smtp-mail.outlook.com:587 con STARTTLS
        - yahoo: smtp.mail.yahoo.com:587 con STARTTLS
        - hotmail: Alias de outlook

Seguridad:
    - STARTTLS: Encripta conexión SMTP (recomendado para puerto 587)
    - SSL/TLS: Encriptación completa (para puerto 465)
    - USE_CREDENTIALS: Requiere autenticación (siempre True en producción)
    - VALIDATE_CERTS: Valida certificados SSL (siempre True en producción)

Example:
    ```python
    from app.config.email_config import get_email_settings, EMAIL_PROVIDERS
    from app.email import EmailService
    
    # Cargar configuración desde .env
    settings = get_email_settings()
    print(f'SMTP Server: {settings.MAIL_SERVER}:{settings.MAIL_PORT}')
    
    # Inicializar servicio de email
    email_service = EmailService(settings)
    
    # Enviar correo
    success = await email_service.send_password_email(
        to='usuario@example.com',
        password='Password123!',
        usuario_nombre='Juan Pérez'
    )
    
    # Usar configuración preestablecida
    gmail_config = EMAIL_PROVIDERS['gmail']
    print(gmail_config['MAIL_SERVER'])  # smtp.gmail.com
    ```

Note:
    Pydantic Settings valida automáticamente tipos y formatos.
    Si falta una variable requerida en .env, lanza ValidationError al iniciar.

See Also:
    - app.email.EmailService: Servicio que usa esta configuración
    - app.routes.email: Endpoints de testing de email
    - app.services.usuario_service: Envía credenciales por email al crear usuarios
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class EmailSettings(BaseSettings):
    """
    Configuración de correo electrónico usando Pydantic Settings.
    
    Similar a configuración de nodemailer transporter en Node.js.
    Carga valores desde variables de entorno (.env) con validación automática.
    
    Attributes:
        MAIL_USERNAME: Email del remitente (usuario SMTP)
        MAIL_PASSWORD: Contraseña o App Password (para Gmail)
        MAIL_FROM: Dirección de email que aparece como remitente
        MAIL_PORT: Puerto SMTP (587 para STARTTLS, 465 para SSL/TLS)
        MAIL_SERVER: Servidor SMTP (ej: smtp.gmail.com)
        MAIL_FROM_NAME: Nombre legible del remitente
        MAIL_STARTTLS: Usar STARTTLS para encriptar (recomendado para puerto 587)
        MAIL_SSL_TLS: Usar SSL/TLS completo (para puerto 465)
        USE_CREDENTIALS: Requiere autenticación SMTP
        VALIDATE_CERTS: Validar certificados SSL del servidor
        TEMPLATE_FOLDER: Carpeta de plantillas de email (Jinja2)
    """
    
    # Configuración SMTP (como en nodemailer)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""
    MAIL_FROM_NAME: str = "JusticIA Sistema"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    
    # Plantillas
    TEMPLATE_FOLDER: str = "app/templates/email"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Configuraciones predefinidas para diferentes proveedores
EMAIL_PROVIDERS = {
    "gmail": {
        "MAIL_SERVER": "smtp.gmail.com",
        "MAIL_PORT": 587,
        "MAIL_STARTTLS": True,
        "MAIL_SSL_TLS": False,
    },
    "outlook": {
        "MAIL_SERVER": "smtp-mail.outlook.com",
        "MAIL_PORT": 587,
        "MAIL_STARTTLS": True,
        "MAIL_SSL_TLS": False,
    },
    "yahoo": {
        "MAIL_SERVER": "smtp.mail.yahoo.com",
        "MAIL_PORT": 587,
        "MAIL_STARTTLS": True,
        "MAIL_SSL_TLS": False,
    },
    "hotmail": {
        "MAIL_SERVER": "smtp-mail.outlook.com",
        "MAIL_PORT": 587,
        "MAIL_STARTTLS": True,
        "MAIL_SSL_TLS": False,
    }
}

def get_email_settings() -> EmailSettings:
    """Obtiene la configuración de correo"""
    return EmailSettings()
