"""add_notebook_table

Revision ID: a1b2c3d4e5f6
Revises: ced897b62461
Create Date: 2026-09-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ced897b62461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'T_Notebook',
        sa.Column('CN_Id_notebook', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre', sa.String(150), nullable=False),
        sa.Column('CN_Id_usuario', sa.String(20), nullable=False),
        sa.Column('CF_Fecha_creacion', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario']),
        sa.PrimaryKeyConstraint('CN_Id_notebook'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('T_Notebook')
