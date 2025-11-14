"""
Modelo SQLAlchemy para estados de usuario.

Define la tabla T_Estado que almacena los estados posibles de cuentas de usuario.

Estados del sistema:
    * ACTIVO (id=1): Usuario con acceso completo
    * INACTIVO (id=2): Usuario deshabilitado temporalmente
    * BLOQUEADO (id=3): Usuario bloqueado por seguridad

Usos:
    * Control de acceso al sistema
    * Deshabilitación temporal de cuentas
    * Bloqueo por seguridad (intentos fallidos, etc.)

Relaciones:
    * 1:N con T_Usuario: Un estado tiene múltiples usuarios

Example:
    >>> from app.db.models import T_Estado
    >>> estado_activo = T_Estado(
    ...     CN_Id_estado=1,
    ...     CT_Nombre_estado="ACTIVO"
    ... )
    >>> estado_inactivo = T_Estado(
    ...     CN_Id_estado=2,
    ...     CT_Nombre_estado="INACTIVO"
    ... )

Note:
    * Los estados se crean en la inicialización de la BD
    * CT_Nombre_estado es único
    * Usuarios INACTIVOS no pueden iniciar sesión

Ver también:
    * app.services.auth_service: Verificación de estado en login
    * app.services.usuario_service: Gestión de estados

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Estado(Base):
    """
    Modelo de estado de usuario.
    
    Attributes:
        CN_Id_estado (int): ID autoincremental (PK).
        CT_Nombre_estado (str): Nombre único del estado (max 50 chars).
        
        usuarios (List[T_Usuario]): Usuarios con este estado.
    """
    __tablename__ = "T_Estado"

    CN_Id_estado: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    CT_Nombre_estado: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    usuarios: Mapped[List["T_Usuario"]] = relationship(back_populates="estado")