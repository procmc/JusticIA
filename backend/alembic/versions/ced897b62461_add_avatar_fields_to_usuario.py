"""add_avatar_fields_to_usuario

Revision ID: ced897b62461
Revises: 001_base_completa
Create Date: 2025-11-06 14:42:06.960530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ced897b62461'
down_revision: Union[str, Sequence[str], None] = '001_base_completa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar columna para ruta de imagen de perfil
    op.add_column('T_Usuario', sa.Column('CT_Avatar_ruta', sa.String(255), nullable=True))
    
    # Agregar columna para tipo/preferencia de avatar (cuando no tiene foto)
    op.add_column('T_Usuario', sa.Column('CT_Avatar_tipo', sa.String(50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('T_Usuario', 'CT_Avatar_tipo')
    op.drop_column('T_Usuario', 'CT_Avatar_ruta')
