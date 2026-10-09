"""
Esquemas (Pydantic) de las rutas de diagnóstico del correo electrónico.

Los usa `app/routes/email.py`: la solicitud del envío de prueba y las respuestas del envío de prueba y de la
consulta de la configuración. La respuesta de la configuración declara uno por uno los datos que el Administrador
puede ver, de modo que la contraseña de la cuenta de correo no tiene por dónde salir (spec 003a, RNF-07.2).

Ver también:
    - app.routes.email: Rutas que usan estos esquemas
"""

from pydantic import BaseModel


class PruebaCorreoSolicitud(BaseModel):
    """Datos del envío de prueba: a quién se envía y la contraseña de ejemplo que lleva el mensaje."""

    email: str
    password: str
    nombre_usuario: str = "Usuario de Prueba"


class PruebaCorreoRespuesta(BaseModel):
    """Resultado del envío de prueba. `success` es falso si el servidor de correo no aceptó el mensaje."""

    success: bool
    message: str


class ConfiguracionCorreoRespuesta(BaseModel):
    """Configuración de correo que se puede mostrar: nunca incluye la contraseña de la cuenta."""

    provider: str
    username: str
    host: str
    port: str
    configured: bool
