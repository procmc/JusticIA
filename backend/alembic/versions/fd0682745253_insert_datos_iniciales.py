"""Insert datos iniciales

Revision ID: fd0682745253
Revises: bf72e9a43bee
Create Date: 2025-09-04 14:29:52.465215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd0682745253'
down_revision: Union[str, Sequence[str], None] = 'bf72e9a43bee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insertar datos iniciales en las tablas de catálogo."""
    
    # Insertar estados de procesamiento
    op.execute("""
        INSERT INTO T_Estado_procesamiento (CT_Nombre_estado) VALUES 
        ('Pendiente'),
        ('Procesado'), 
        ('Error')
    """)
    
    # Insertar roles
    op.execute("""
        INSERT INTO T_Rol (CT_Nombre_rol) VALUES 
        ('Administrador'),
        ('Usuario Judicial')
    """)
    
    # Insertar estados de usuario
    op.execute("""
        INSERT INTO T_Estado (CT_Nombre_estado) VALUES 
        ('Activo'),
        ('Inactivo')
    """)
    
    # Insertar tipos de acción
    op.execute("""
        INSERT INTO T_Tipo_accion (CT_Nombre_tipo_accion) VALUES 
        ('Consulta'),
        ('Carga Documentos'),
        ('Busqueda Similares'),
        ('Login'),
        ('Crear_Usuario'),
        ('Editar_Usuario'),
        ('Consultar_Bitacora'),
        ('Exportar Bitacora')
    """)


def downgrade() -> None:
    """Eliminar datos iniciales si es necesario hacer rollback."""
    
    # Eliminar en orden inverso para evitar problemas de foreign keys
    op.execute("DELETE FROM T_Tipo_accion WHERE CT_Nombre_tipo_accion IN ('Consulta', 'Carga Documentos', 'Busqueda Similares', 'Login', 'Crear_Usuario', 'Editar_Usuario', 'Consultar_Bitacora', 'Exportar Bitacora')")
    op.execute("DELETE FROM T_Estado WHERE CT_Nombre_estado IN ('Activo', 'Inactivo')")
    op.execute("DELETE FROM T_Rol WHERE CT_Nombre_rol IN ('Administrador', 'Usuario Judicial')")
    op.execute("DELETE FROM T_Estado_procesamiento WHERE CT_Nombre_estado IN ('Pendiente', 'Procesado', 'Error')")
