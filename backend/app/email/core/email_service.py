"""
Servicio de correo electrónico - Solo lógica de envío
HTML/CSS separado en templates/email_template.py
"""
import aiosmtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from dataclasses import dataclass
from dotenv import load_dotenv

from ..templates.email_template import EmailTemplate
from ..types.email_types import EmailData

# Cargar variables de entorno
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
    Servicio de correo electrónico - Solo lógica de envío
    Plantillas HTML separadas en EmailTemplate
    """
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.template = EmailTemplate()
    
    def generate_random_password(self, length: int = 8) -> str:
        """Genera contraseña aleatoria"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    async def send_email(self, to: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Envía correo electrónico básico
        """
        try:
            # Crear mensaje
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
            
            # Enviar correo
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
            print(f"❌ Error enviando correo: {e}")
            return False
    
    async def send_password_email(self, to: str, password: str, usuario_nombre: str = "Usuario") -> bool:
        """
        Envía correo con contraseña usando plantilla separada
        Mantiene compatibilidad con código existente
        """
        subject = "Tu contraseña de acceso - JusticIA"
        
        # Usar plantilla separada para generar HTML
        html_content = self.template.generar_correo_credenciales(
            usuario_nombre=usuario_nombre,
            password=password
        )
        
        # Texto plano desde plantilla
        text_content = self.template.obtener_texto_plano_credenciales(
            usuario_nombre=usuario_nombre,
            password=password
        )
        
        return await self.send_email(to, subject, html_content, text_content)
    
    async def enviar_correo_universal(self, email_data: EmailData) -> bool:
        """
        Envía correo usando plantilla universal
        """
        try:
            # Generar HTML usando plantilla separada
            html_content = self.template.generar_correo_universal(
                asunto=email_data.asunto,
                titulo=email_data.titulo,
                mensaje=email_data.mensaje,
                datos_adicionales=email_data.datos_adicionales,
                mostrar_credenciales=email_data.mostrar_credenciales,
                credenciales=email_data.credenciales
            )
            
            return await self.send_email(
                to=email_data.to,
                subject=email_data.asunto,
                html_content=html_content
            )
            
        except Exception as e:
            print(f"❌ Error enviando correo universal: {e}")
            return False

# Configuraciones predefinidas (mantener las existentes)
def get_gmail_config(username: str, password: str) -> EmailConfig:
    return EmailConfig(
        host="smtp.gmail.com",
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_outlook_config(username: str, password: str) -> EmailConfig:
    return EmailConfig(
        host="smtp-mail.outlook.com", 
        port=587,
        username=username,
        password=password,
        use_tls=True
    )

def get_email_config_from_env() -> EmailConfig:
    """Obtiene configuración desde variables de entorno"""
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
    username = os.getenv("EMAIL_USERNAME", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    
    if provider == "gmail":
        return get_gmail_config(username, password)
    elif provider == "outlook":
        return get_outlook_config(username, password)
    else:
        return EmailConfig(
            host=os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            port=int(os.getenv("EMAIL_PORT", "587")),
            username=username,
            password=password,
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
        )
