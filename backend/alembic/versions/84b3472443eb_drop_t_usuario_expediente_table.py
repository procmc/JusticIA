"""drop_t_usuario_expediente_table

Revision ID: 84b3472443eb
Revises: a6132e715c2f
Create Date: 2025-09-03 17:46:19.943090

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84b3472443eb'
down_revision: Union[str, Sequence[str], None] = 'a6132e715c2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Eliminar la tabla T_Usuario_Expediente
    op.drop_table('T_Usuario_Expediente')


def downgrade() -> None:
    """Downgrade schema."""
    # Recrear la tabla T_Usuario_Expediente en caso de rollback
    op.create_table(
        'T_Usuario_Expediente',
        sa.Column('CN_Id_usuario', sa.Integer(), nullable=False),
        sa.Column('CN_Id_expediente', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['CN_Id_expediente'], ['T_Expediente.CN_Id_expediente'], ),
        sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario'], ),
        sa.PrimaryKeyConstraint('CN_Id_usuario', 'CN_Id_expediente')
    )
