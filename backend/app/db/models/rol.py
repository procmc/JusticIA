"""
Modelo SQLAlchemy para roles de usuario.

Define la tabla T_Rol que almacena los roles del sistema para control de acceso
basado en roles (RBAC).

Roles del sistema:
    * ADMIN (id=1): Acceso completo a administración y gestión
    * USER (id=2): Acceso a consultas y búsquedas

Permisos por rol:
    * ADMIN:
      - Gestión de usuarios
      - Consulta de bitácora
      - Todas las funcionalidades de USER
    
    * USER:
      - Asistente virtual (Chat RAG)
      - Búsqueda de casos similares
      - Ingesta de documentos

Relaciones:
    * 1:N con T_Usuario: Un rol tiene múltiples usuarios

Example:
    >>> from app.db.models import T_Rol
    >>> rol_admin = T_Rol(
    ...     CN_Id_rol=1,
    ...     CT_Nombre_rol="ADMIN"
    ... )
    >>> rol_user = T_Rol(
    ...     CN_Id_rol=2,
    ...     CT_Nombre_rol="USER"
    ... )

Note:
    * Los roles se crean en la inicialización de la BD
    * CT_Nombre_rol es único
    * No se deben eliminar roles con usuarios asociados

Ver también:
    * app.common.roles: Constantes de roles para frontend
    * app.routes.auth: Verificación de roles en endpoints
    * app.services.usuario_service: Asignación de roles

Authors:
    JusticIA Team

Version:
    1.0.0
"""
from typing import List
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class T_Rol(Base):
	"""
	Modelo de rol de usuario.
	
	Attributes:
		CN_Id_rol (int): ID autoincremental (PK).
		CT_Nombre_rol (str): Nombre único del rol (max 50 chars).
		
		usuarios (List[T_Usuario]): Usuarios con este rol.
	"""
	__tablename__ = "T_Rol"

	CN_Id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	CT_Nombre_rol: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

	# Relaciones
	usuarios: Mapped[List["T_Usuario"]] = relationship(back_populates="rol")