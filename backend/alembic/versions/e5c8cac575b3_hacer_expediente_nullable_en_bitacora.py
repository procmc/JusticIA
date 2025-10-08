"""hacer_expediente_nullable_en_bitacora

Revision ID: e5c8cac575b3
Revises: c039f8f03469
Create Date: 2025-10-08 10:45:11.908278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5c8cac575b3'
down_revision: Union[str, Sequence[str], None] = 'c039f8f03469'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Hacer el campo CN_Id_expediente nullable en T_Bitacora."""
    # Modificar columna para permitir NULL
    op.alter_column(
        'T_Bitacora',
        'CN_Id_expediente',
        existing_type=sa.BigInteger(),
        nullable=True
    )


def downgrade() -> None:
    """Revertir: hacer CN_Id_expediente NOT NULL nuevamente."""
    # Advertencia: esto fallará si hay registros con NULL
    op.alter_column(
        'T_Bitacora',
        'CN_Id_expediente',
        existing_type=sa.BigInteger(),
        nullable=False
    )
