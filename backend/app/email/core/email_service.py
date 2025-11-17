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
    
    async def send_recovery_code_email(self, to_email: str, user_name: str, recovery_code: str) -> bool:
        """Envía email con código de recuperación de contraseña"""
        try:
            subject = "Código de Recuperación de Contraseña - JusticIA"
            
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                    <h2 style="color: #2c3e50; margin-bottom: 20px;">🔐 Recuperación de Contraseña</h2>
                    <p style="color: #34495e; font-size: 16px; margin-bottom: 15px;">
                        Hola <strong>{user_name}</strong>,
                    </p>
                    <p style="color: #34495e; font-size: 14px; margin-bottom: 25px;">
                        Has solicitado recuperar tu contraseña. Usa el siguiente código de verificación:
                    </p>
                    <div style="background-color: #3498db; color: white; padding: 15px; border-radius: 5px; font-size: 24px; font-weight: bold; letter-spacing: 2px; margin: 20px 0;">
                        {recovery_code}
                    </div>
                    <p style="color: #e74c3c; font-size: 12px; margin-top: 20px;">
                        ⚠️ Este código expira en 15 minutos por seguridad.
                    </p>
                    <p style="color: #7f8c8d; font-size: 12px; margin-top: 15px;">
                        Si no solicitaste este código, ignora este mensaje.
                    </p>
                </div>
                <div style="text-align: center; margin-top: 20px; color: #95a5a6; font-size: 12px;">
                    Sistema JusticIA - Gestión de Documentos Jurídicos
                </div>
            </div>
            """
            
            text_content = f"""
            Recuperación de Contraseña - JusticIA
            
            Hola {user_name},
            
            Has solicitado recuperar tu contraseña. 
            Tu código de verificación es: {recovery_code}
            
            Este código expira en 15 minutos por seguridad.
            
            Si no solicitaste este código, ignora este mensaje.
            
            Sistema JusticIA
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"❌ Error enviando email de recuperación: {e}")
            return False
    
    async def send_password_reset_email(self, to_email: str, user_name: str, new_password: str) -> bool:
        """Envía email con nueva contraseña restablecida por el administrador"""
        try:
            subject = "Contraseña Restablecida por Administrador - JusticIA"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; margin: 40px;">
                <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px;">
                    <div style="background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                        <h1 style="margin: 0;">JusticIA</h1>
                    </div>
                    <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                        <h2>Hola {user_name},</h2>
                        <p>Un administrador ha restablecido tu contraseña en el sistema JusticIA. Tu nueva contraseña temporal es:</p>
                        
                        <div style="background: #f3f4f6; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 18px; font-weight: bold; text-align: center; margin: 20px 0;">
                            {new_password}
                        </div>
                        
                        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 6px; margin: 20px 0;">
                            <strong>⚠️ Importante:</strong> Esta es una contraseña temporal. Debes cambiarla obligatoriamente al iniciar sesión.
                        </div>
                        
                        <p><strong>Recomendaciones:</strong></p>
                        <ul>
                            <li>Guarda esta contraseña en un lugar seguro</li>
                            <li>Cámbiala inmediatamente después del primer acceso</li>
                            <li>No compartas esta información con terceros</li>
                        </ul>
                        
                        <p>Si no esperabas este cambio o tienes dudas, contacta al administrador del sistema.</p>
                    </div>
                    <div style="text-align: center; color: #666; margin-top: 20px;">
                        <p style="font-size: 12px;">Este es un mensaje automático, no responder a este correo.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            Contraseña Restablecida por Administrador - JusticIA
            
            Hola {user_name},
            
            Un administrador ha restablecido tu contraseña en el sistema JusticIA.
            Tu nueva contraseña temporal es: {new_password}
            
            IMPORTANTE: Esta es una contraseña temporal. Debes cambiarla obligatoriamente al iniciar sesión.
            
            Recomendaciones:
            - Guarda esta contraseña en un lugar seguro
            - Cámbiala inmediatamente después del primer acceso
            - No compartas esta información con terceros
            
            Si no esperabas este cambio o tienes dudas, contacta al administrador del sistema.
            
            Sistema JusticIA
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            print(f"❌ Error enviando email de restablecimiento: {e}")
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
