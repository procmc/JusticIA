"""
Tipos para el sistema de correo electrónico
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional

class EmailData(BaseModel):
    """Datos para enviar correo con plantilla universal"""
    to: str
    asunto: str
    titulo: str
    mensaje: str
    datos_adicionales: Optional[Dict[str, Any]] = None
    mostrar_credenciales: bool = False
    credenciales: Optional[Dict[str, str]] = None
