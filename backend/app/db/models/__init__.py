from .base import Base
from .rol import T_Rol
from .usuario import T_Usuario
from .estado import T_Estado
from .estado_procesamiento import T_Estado_procesamiento
from .expediente import T_Expediente
from .documento import T_Documento
from .tipo_accion import T_Tipo_accion
from .bitacora import T_Bitacora
from .usuario_expediente import T_Usuario_Expediente
from .expediente_documento import T_Expediente_Documento  # <-- nuevo

__all__ = [
    "Base",
    "T_Rol",
    "T_Usuario",
    "T_Estado",
    "T_Estado_procesamiento",
    "T_Expediente",
    "T_Documento",
    "T_Tipo_accion",
    "T_Bitacora",
    "T_Usuario_Expediente",
    "T_Expediente_Documento",
]