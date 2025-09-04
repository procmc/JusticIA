"""
Módulo de correo electrónico de JusticIA
Estructura organizada: core (lógica) + templates (HTML/CSS) + types (modelos)
"""

from .core.email_service import EmailService, EmailConfig, get_email_config_from_env
from .templates.email_template import EmailTemplate
from .types.email_types import EmailData

__all__ = [
    "EmailService",
    "EmailConfig", 
    "EmailTemplate",
    "EmailData",
    "get_email_config_from_env"
]
