"""Insert initial data

Revision ID: 2aed2bedb036
Revises: 057e53b7a916
Create Date: 2025-09-04 13:49:44.087722

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2aed2bedb036'
down_revision: Union[str, Sequence[str], None] = '057e53b7a916'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert initial data."""
    # T_Estado_procesamiento
    op.execute("""
        INSERT INTO T_Estado_procesamiento (CT_Nombre_estado) VALUES 
        ('Pendiente'),
        ('Procesado'), 
        ('Error')
    """)
    
    # T_Rol
    op.execute("""
        INSERT INTO T_Rol (CT_Nombre_rol) VALUES 
        ('Administrador'),
        ('Usuario Judicial')
    """)
    
    # T_Estado
    op.execute("""
        INSERT INTO T_Estado (CT_Nombre_estado) VALUES 
        ('Activo'),
        ('Inactivo')
    """)
    
    # T_Tipo_accion
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
    """Remove initial data."""
    op.execute("DELETE FROM T_Tipo_accion")
    op.execute("DELETE FROM T_Estado")
    op.execute("DELETE FROM T_Rol")
    op.execute("DELETE FROM T_Estado_procesamiento")
