"""
Servicio de correo electrónico - Solo lógica de envío
HTML/CSS separado en templates/email_template.py

El envío tiene un tiempo máximo TOTAL (RF-03.16), clasifica la causa de cada fallo en el registro sin
escribir nunca el texto del error ni credenciales (RF-03.17) y arma el mensaje en UTF-8 (RF-03.18). Los
`send_*` siguen devolviendo `bool` y sin lanzar: quien los llama decide qué hacer con el fallo.

Ver también: `app/utils/reloj.py` (reloj que mide el plazo), `app/utils/enmascarar.py` (correos en los registros).
"""
import aiosmtplib
import logging
import math
import secrets
import string
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional
import os
from dataclasses import dataclass
from dotenv import load_dotenv

from ...utils.enmascarar import enmascarar_correo
from ...utils.reloj import obtener_reloj
from ..templates.email_template import EmailTemplate
from ..types.email_types import EmailData

logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Tiempo máximo de un envío completo, en segundos (RF-03.16). Se cambia con la variable EMAIL_TIMEOUT.
TIEMPO_MAXIMO_POR_OMISION = 15.0


@dataclass
class EmailConfig:
    """Configuración de correo - como nodemailer transporter"""
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    from_name: str = "ServIA Sistema"
    timeout: float = TIEMPO_MAXIMO_POR_OMISION


def _revisar_configuracion(config: EmailConfig) -> Optional[str]:
    """Devuelve la causa «configuracion» si la cuenta no sirve para enviar (sin llamar a la librería), o None."""
    if not config.host or not config.username or not config.password:
        return "configuracion"
    if not isinstance(config.port, int) or not 1 <= config.port <= 65535:
        return "configuracion"
    return None


def clasificar_causa(error: BaseException) -> str:
    """Clasifica un fallo de envío para el registro: nunca se escribe el texto del error, solo esta causa.

    El orden importa: `SMTPTimeoutError` es a la vez `SMTPException`, `TimeoutError` y `OSError`, y
    `SMTPConnectError` es `ConnectionError` y `OSError`; se evalúa de lo más específico a lo más general.
    """
    if isinstance(error, (TimeoutError, aiosmtplib.SMTPTimeoutError)):
        return "tiempo_agotado"
    if isinstance(error, aiosmtplib.SMTPAuthenticationError):
        return "autenticacion"
    if isinstance(error, (aiosmtplib.SMTPRecipientRefused, aiosmtplib.SMTPRecipientsRefused,
                          aiosmtplib.SMTPSenderRefused)):
        return "rechazo"
    if isinstance(error, (ConnectionError, OSError, aiosmtplib.SMTPConnectError,
                          aiosmtplib.SMTPServerDisconnected)):
        return "conexion"
    if isinstance(error, aiosmtplib.SMTPException):
        return "servidor"
    return "inesperado"


class EmailService:
    """
    Servicio de correo electrónico - Solo lógica de envío
    Plantillas HTML separadas en EmailTemplate
    """

    def __init__(self, config: EmailConfig, reloj=None):
        self.config = config
        self.template = EmailTemplate()
        # Si no se inyecta un reloj, se pide el del sistema en cada envío (no aquí): así el servicio que se
        # crea al importar el módulo usa el reloj que una prueba haya instalado (RA-02.9).
        self._reloj = reloj

    def generate_random_password(self, length: int = 8) -> str:
        """Genera contraseña aleatoria"""
        characters = string.ascii_letters + string.digits
        return ''.join(secrets.choice(characters) for _ in range(length))

    async def send_email(self, to: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Envía correo electrónico básico.

        Nunca lanza: devuelve False si el envío no se completó (cuenta sin configurar, error del servidor,
        más de `config.timeout` segundos...). El registro dice la causa clasificada y el tipo de la excepción,
        con el destinatario enmascarado; nunca el texto del error, que puede traer usuarios o claves.
        """
        destinatario = enmascarar_correo(to)
        causa = _revisar_configuracion(self.config)
        if causa:
            logger.warning("Correo a %s no enviado: causa=%s", destinatario, causa)
            return False

        try:
            # Crear mensaje. El asunto y el nombre del remitente van como encabezados UTF-8 explícitos
            # (palabras codificadas, RFC 2047): no se depende de la conversión implícita de Python, que
            # codificaría también la dirección del remitente cuando el nombre lleva tilde o «ñ».
            message = MIMEMultipart("alternative")
            message["From"] = formataddr((self.config.from_name, self.config.username), charset="utf-8")
            message["To"] = to
            message["Subject"] = Header(subject, "utf-8")

            # Agregar contenido texto plano si existe
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                message.attach(text_part)

            # Agregar contenido HTML
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)

            # Enviar correo. El límite TOTAL lo pone el reloj (conexión, saludo, autenticación y envío
            # juntos); `timeout` de la librería es una cota por operación y solo evita sockets colgados.
            limite = self.config.timeout
            reloj = self._reloj or obtener_reloj()
            await reloj.con_limite(
                aiosmtplib.send(
                    message,
                    hostname=self.config.host,
                    port=self.config.port,
                    start_tls=self.config.use_tls,
                    username=self.config.username,
                    password=self.config.password,
                    timeout=limite,
                ),
                limite,
            )

            return True

        except Exception as e:
            logger.warning(
                "Correo a %s no enviado: causa=%s tipo=%s", destinatario, clasificar_causa(e), type(e).__name__
            )
            return False

    async def send_password_email(self, to: str, password: str, usuario_nombre: str = "Usuario") -> bool:
        """
        Envía correo con contraseña usando plantilla separada
        Mantiene compatibilidad con código existente
        """
        subject = "Tu contraseña de acceso - ServIA"
        
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
            logger.warning("Correo universal no enviado: error al armarlo, tipo=%s", type(e).__name__)
            return False
    
    async def send_recovery_code_email(self, to_email: str, user_name: str, recovery_code: str) -> bool:
        """Envía email con código de recuperación de contraseña"""
        try:
            subject = "Código de Recuperación de Contraseña - ServIA"
            
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
                    Sistema ServIA - Gestión de Documentos Jurídicos
                </div>
            </div>
            """
            
            text_content = f"""
            Recuperación de Contraseña - ServIA
            
            Hola {user_name},
            
            Has solicitado recuperar tu contraseña. 
            Tu código de verificación es: {recovery_code}
            
            Este código expira en 15 minutos por seguridad.
            
            Si no solicitaste este código, ignora este mensaje.
            
            Sistema ServIA
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.warning("Correo de recuperación no enviado: error al armarlo, tipo=%s", type(e).__name__)
            return False
    
    async def send_password_reset_email(self, to_email: str, user_name: str, new_password: str) -> bool:
        """Envía email con nueva contraseña restablecida por el administrador"""
        try:
            subject = "Contraseña Restablecida por Administrador - ServIA"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial, sans-serif; margin: 40px;">
                <div style="max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; border-radius: 8px;">
                    <div style="background: #2563eb; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                        <h1 style="margin: 0;">ServIA</h1>
                    </div>
                    <div style="background: white; padding: 30px; border-radius: 0 0 8px 8px;">
                        <h2>Hola {user_name},</h2>
                        <p>Un administrador ha restablecido tu contraseña en el sistema ServIA. Tu nueva contraseña temporal es:</p>
                        
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
            Contraseña Restablecida por Administrador - ServIA
            
            Hola {user_name},
            
            Un administrador ha restablecido tu contraseña en el sistema ServIA.
            Tu nueva contraseña temporal es: {new_password}
            
            IMPORTANTE: Esta es una contraseña temporal. Debes cambiarla obligatoriamente al iniciar sesión.
            
            Recomendaciones:
            - Guarda esta contraseña en un lugar seguro
            - Cámbiala inmediatamente después del primer acceso
            - No compartas esta información con terceros
            
            Si no esperabas este cambio o tienes dudas, contacta al administrador del sistema.
            
            Sistema ServIA
            """
            
            return await self.send_email(to_email, subject, html_content, text_content)
            
        except Exception as e:
            logger.warning("Correo de restablecimiento no enviado: error al armarlo, tipo=%s", type(e).__name__)
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

def _leer_tiempo_maximo() -> float:
    """Lee EMAIL_TIMEOUT (segundos). Sin la variable, 15; si no es un número finito mayor que cero, 15 y una
    advertencia que nombra la variable (sin repetir su valor)."""
    crudo = os.getenv("EMAIL_TIMEOUT")
    if crudo is None:
        return TIEMPO_MAXIMO_POR_OMISION
    try:
        valor = float(crudo)
    except ValueError:
        valor = float("nan")
    if not math.isfinite(valor) or valor <= 0:
        logger.warning(
            "EMAIL_TIMEOUT no es un número mayor que cero; se usa el tiempo máximo por omisión de %s s.",
            TIEMPO_MAXIMO_POR_OMISION,
        )
        return TIEMPO_MAXIMO_POR_OMISION
    return valor

def get_email_config_from_env() -> EmailConfig:
    """Obtiene configuración desde variables de entorno"""
    provider = os.getenv("EMAIL_PROVIDER", "gmail").lower()
    username = os.getenv("EMAIL_USERNAME", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    timeout = _leer_tiempo_maximo()

    if provider == "gmail":
        config = get_gmail_config(username, password)
    elif provider == "outlook":
        config = get_outlook_config(username, password)
    else:
        config = EmailConfig(
            host=os.getenv("EMAIL_HOST", "smtp.gmail.com"),
            port=int(os.getenv("EMAIL_PORT", "587")),
            username=username,
            password=password,
            use_tls=os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
        )
    config.timeout = timeout
    return config
