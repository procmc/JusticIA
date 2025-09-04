"""
Servicio de envío de correos electrónicos
Equivalente a Nodemailer en Node.js - usando aiosmtplib
"""

import aiosmtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (como en Node.js)
load_dotenv()

@dataclass
class EmailConfig:
    """Configuración de correo - como nodemailer transporter"""
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    from_name: str = "JusticIA Sistema"

class EmailService:
    """
    Servicio de correo electrónico - Similar a Nodemailer
    
    Uso:
    email_service = EmailService(config)
    await email_service.send_password_email("user@email.com", "123456")
    """
    
    def __init__(self, config: EmailConfig):
        self.config = config
    
    def generate_random_password(self, length: int = 8) -> str:
        """Genera contraseña aleatoria como en Node.js"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    async def send_email(self, to: str, subject: str, html_content: str, text_content: Optional[str] = None):
        """
        Envía correo electrónico - Equivalente a transporter.sendMail en nodemailer
        
        Args:
            to: Destinatario
            subject: Asunto
            html_content: Contenido HTML
            text_content: Contenido texto plano (opcional)
        """
        try:
            # Crear mensaje (como en nodemailer)
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.config.from_name} <{self.config.username}>"
            message["To"] = to
            message["Subject"] = subject
            
            # Agregar contenido texto plano si existe
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                message.attach(text_part)
            
            # Agregar contenido HTML
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)
            
            # Enviar correo (como transporter.sendMail)
            await aiosmtplib.send(
                message,
                hostname=self.config.host,
                port=self.config.port,
                start_tls=self.config.use_tls,
                username=self.config.username,
                password=self.config.password,
            )
            
            return True
            
        except Exception as e:
            print(f"Error enviando correo: {e}")
            return False
    
    async def send_password_email(self, to: str, password: str, usuario_nombre: str = "Usuario"):
        """
        Envía correo con contraseña - Función específica para usuarios
        
        Args:
            to: Email del usuario
            password: Contraseña generada
            usuario_nombre: Nombre del usuario
        """
        subject = "Tu contraseña de acceso - JusticIA"
        
        # Plantilla HTML (como en nodemailer con templates)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: white; padding: 30px; border-radius: 0 0 8px 8px; }}
                .password {{ background: #f3f4f6; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 18px; font-weight: bold; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>JusticIA - Sistema de Información</h1>
                </div>
                <div class="content">
                    <h2>Hola {usuario_nombre},</h2>
                    <p>Se ha creado tu cuenta en el sistema JusticIA. Tu contraseña de acceso es:</p>
                    
                    <div class="password">{password}</div>
                    
                    <p><strong>Importante:</strong></p>
                    <ul>
                        <li>Guarda esta contraseña en un lugar seguro</li>
                        <li>Se recomienda cambiarla después del primer acceso</li>
                        <li>No compartas esta información con terceros</li>
                    </ul>
                    
                    <p>Puedes acceder al sistema usando tu email y esta contraseña.</p>
                </div>
                <div class="footer">
                    <p>Este es un mensaje automático, no responder a este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Versión texto plano
        text_content = f"""
        Hola {usuario_nombre},

        Se ha creado tu cuenta en el sistema JusticIA.
        Tu contraseña de acceso es: {password}

        Importante:
        - Guarda esta contraseña en un lugar seguro
        - Se recomienda cambiarla después del primer acceso
        - No compartas esta información con terceros

        Puedes acceder al sistema usando tu email y esta contraseña.

        --
        Sistema JusticIA
        """
        
        return await self.send_email(to, subject, html_content, text_content)

# Configuraciones predefinidas (como en nodemailer)
def get_gmail_config(username: str, password: str) -> EmailConfig:
    """Configuración para Gmail - como nodemailer Gmail transporter"""
    return EmailConfig(
        host="smtp.gmail.com",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_outlook_config(username: str, password: str) -> EmailConfig:
    """Configuración para Outlook - como nodemailer Outlook transporter"""
    return EmailConfig(
        host="smtp-mail.outlook.com", 
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_yahoo_config(username: str, password: str) -> EmailConfig:
    """Configuración para Yahoo - como nodemailer Yahoo transporter"""
    return EmailConfig(
        host="smtp.mail.yahoo.com",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_zoho_config(username: str, password: str) -> EmailConfig:
    """Configuración para Zoho Mail"""
    return EmailConfig(
        host="smtp.zoho.com",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_office365_config(username: str, password: str) -> EmailConfig:
    """Configuración para Office 365"""
    return EmailConfig(
        host="smtp.office365.com",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_sendgrid_config(username: str, password: str) -> EmailConfig:
    """Configuración para SendGrid"""
    return EmailConfig(
        host="smtp.sendgrid.net",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_mailgun_config(username: str, password: str) -> EmailConfig:
    """Configuración para Mailgun"""
    return EmailConfig(
        host="smtp.mailgun.org",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_mailtrap_config(username: str, password: str) -> EmailConfig:
    """Configuración para Mailtrap (testing)"""
    return EmailConfig(
        host="smtp.mailtrap.io",
        port=2525,
        username=username,
        password=password,
        use_tls=True
    )

# Función helper para obtener configuración desde variables de entorno
def get_email_config_from_env() -> EmailConfig:
    """
    Obtiene configuración desde variables de entorno
    Similar a process.env en Node.js
    """
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
    username = os.getenv("EMAIL_USERNAME", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    
    if provider == "gmail":
        return get_gmail_config(username, password)
    elif provider == "outlook":
        return get_outlook_config(username, password)
    elif provider == "yahoo":
        return get_yahoo_config(username, password)
    elif provider == "zoho":
        return get_zoho_config(username, password)
    elif provider == "office365":
        return get_office365_config(username, password)
    elif provider == "sendgrid":
        return get_sendgrid_config(username, password)
    elif provider == "mailgun":
        return get_mailgun_config(username, password)
    elif provider == "mailtrap":
        return get_mailtrap_config(username, password)
    else:
        # Configuración personalizada
        return EmailConfig(
            host=os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            port=int(os.getenv("EMAIL_PORT", "587")),
            username=username,
            password=password,
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
        )
