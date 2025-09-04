"""
Configuración para envío de correos electrónicos
Soporta Gmail, Outlook, y otros proveedores SMTP
Similar a Nodemailer en Node.js
"""

from pydantic import BaseSettings
from typing import Optional
import os

class EmailSettings(BaseSettings):
    """Configuración de correo electrónico - Similar a nodemailer transporter"""
    
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
