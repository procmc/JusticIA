"""update_usuario_cedula_pk_and_add_names

Revision ID: 8911802c606d
Revises: 84b3472443eb
Create Date: 2025-01-27 12:50:45.763851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8911802c606d'
down_revision: Union[str, Sequence[str], None] = '84b3472443eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Como estamos en una nueva BD, podemos aplicar todos los cambios directamente
    
    # 1. Agregar nuevas columnas como nullable primero
    op.add_column('T_Usuario', sa.Column('CT_Nombre', sa.String(length=100), nullable=True))
    op.add_column('T_Usuario', sa.Column('CT_Apellido_uno', sa.String(length=100), nullable=True))
    op.add_column('T_Usuario', sa.Column('CT_Apellido_dos', sa.String(length=100), nullable=True))
    
    # 2. Actualizar registros existentes con valores por defecto
    op.execute("UPDATE T_Usuario SET CT_Nombre = 'Nombre Pendiente' WHERE CT_Nombre IS NULL")
    op.execute("UPDATE T_Usuario SET CT_Apellido_uno = 'Apellido Pendiente' WHERE CT_Apellido_uno IS NULL")
    
    # 3. Hacer NOT NULL las columnas requeridas
    op.alter_column('T_Usuario', 'CT_Nombre', nullable=False, existing_type=sa.String(length=100))
    op.alter_column('T_Usuario', 'CT_Apellido_uno', nullable=False, existing_type=sa.String(length=100))
    
    # 4. Cambiar CN_Id_usuario de INTEGER a STRING
    op.alter_column('T_Usuario', 'CN_Id_usuario',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=20),
               existing_nullable=False,
               autoincrement=False)
    
    # 5. Actualizar T_Bitacora FK
    op.alter_column('T_Bitacora', 'CN_Id_usuario',
               existing_type=sa.INTEGER(),
               type_=sa.String(length=20),
               existing_nullable=False)
    
    # 6. Crear tabla T_Usuario_Expediente
    op.create_table('T_Usuario_Expediente',
    sa.Column('CN_Id_usuario', sa.String(length=20), nullable=False),
    sa.Column('CN_Id_expediente', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['CN_Id_expediente'], ['T_Expediente.CN_Id_expediente'], ),
    sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario'], ),
    sa.PrimaryKeyConstraint('CN_Id_usuario', 'CN_Id_expediente')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Eliminar tabla T_Usuario_Expediente
    op.drop_table('T_Usuario_Expediente')
    
    # 2. Cambiar T_Bitacora FK de vuelta a INTEGER
    op.alter_column('T_Bitacora', 'CN_Id_usuario',
               existing_type=sa.String(length=20),
               type_=sa.INTEGER(),
               existing_nullable=False)
    
    # 3. Cambiar CN_Id_usuario de STRING a INTEGER (con autoincrement)
    op.alter_column('T_Usuario', 'CN_Id_usuario',
               existing_type=sa.String(length=20),
               type_=sa.INTEGER(),
               existing_nullable=False,
               autoincrement=True)
    
    # 4. Eliminar columnas nuevas
    op.drop_column('T_Usuario', 'CT_Apellido_dos')
    op.drop_column('T_Usuario', 'CT_Apellido_uno')
    op.drop_column('T_Usuario', 'CT_Nombre')
