"""new_database_full_schema

Revision ID: ecdfba240068
Revises: 84b3472443eb
Create Date: 2025-09-04 12:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecdfba240068'
down_revision: Union[str, Sequence[str], None] = '84b3472443eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for new database with updated usuario structure."""
    
    # Crear tabla T_Usuario con cédula como PK y campos de nombres
    op.create_table('T_Usuario',
        sa.Column('CN_Id_usuario', sa.String(length=20), nullable=False),
        sa.Column('CT_Nombre_usuario', sa.String(length=50), nullable=False),
        sa.Column('CT_Nombre', sa.String(length=100), nullable=False),
        sa.Column('CT_Apellido_uno', sa.String(length=100), nullable=False),
        sa.Column('CT_Apellido_dos', sa.String(length=100), nullable=True),
        sa.Column('CT_Correo', sa.String(length=100), nullable=False),
        sa.Column('CT_Contrasenna', sa.String(length=255), nullable=False),
        sa.Column('CN_Id_rol', sa.Integer(), nullable=True),
        sa.Column('CN_Id_estado', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['CN_Id_estado'], ['T_Estado.CN_Id_estado'], ),
        sa.ForeignKeyConstraint(['CN_Id_rol'], ['T_Rol.CN_Id_rol'], ),
        sa.PrimaryKeyConstraint('CN_Id_usuario'),
        sa.UniqueConstraint('CT_Correo', name='uq_usuario_correo'),
        sa.UniqueConstraint('CT_Nombre_usuario', name='uq_usuario_nombre')
    )
    
    # Crear tabla T_Usuario_Expediente con FK a string
    op.create_table('T_Usuario_Expediente',
        sa.Column('CN_Id_usuario', sa.String(length=20), nullable=False),
        sa.Column('CN_Id_expediente', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['CN_Id_expediente'], ['T_Expediente.CN_Id_expediente'], ),
        sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario'], ),
        sa.PrimaryKeyConstraint('CN_Id_usuario', 'CN_Id_expediente')
    )
    
    # Actualizar T_Bitacora para usar string FK
    op.alter_column('T_Bitacora', 'CN_Id_usuario',
                   existing_type=sa.INTEGER(),
                   type_=sa.String(length=20),
                   existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revertir cambios en T_Bitacora
    op.alter_column('T_Bitacora', 'CN_Id_usuario',
                   existing_type=sa.String(length=20),
                   type_=sa.INTEGER(),
                   existing_nullable=False)
    
    # Eliminar tablas
    op.drop_table('T_Usuario_Expediente')
    op.drop_table('T_Usuario')
