"""hacer usuario nullable en bitacora

Revision ID: hacer_usuario_nullable
Revises: e5c8cac575b3
Create Date: 2025-10-09 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'hacer_usuario_nullable'
down_revision: Union[str, None] = 'e5c8cac575b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Hacer el campo CN_Id_usuario nullable en T_Bitacora para permitir registros sin usuario conocido."""
    op.alter_column(
        'T_Bitacora',
        'CN_Id_usuario',
        existing_type=sa.String(length=20),
        nullable=True,
        existing_nullable=False
    )


def downgrade() -> None:
    """Revertir: Hacer CN_Id_usuario NOT NULL nuevamente."""
    # Primero eliminar registros con usuario NULL (si existen)
    op.execute("DELETE FROM \"T_Bitacora\" WHERE \"CN_Id_usuario\" IS NULL")
    
    # Luego hacer el campo NOT NULL
    op.alter_column(
        'T_Bitacora',
        'CN_Id_usuario',
        existing_type=sa.String(length=20),
        nullable=False,
        existing_nullable=True
    )
