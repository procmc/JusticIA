"""baja logica de documentos

Spec 009b, cambio GG1 (RF-19.111, RN-01.101): agrega T_Documento.CF_Fecha_baja y T_Documento.CN_Id_usuario_baja (clave foránea a
T_Usuario). NULL = activo; al quitar una fuente de un notebook la fila no se borra, queda con la fecha y hora de la baja y quién
la quitó. No cambia los datos existentes (todos quedan activos).

Revision ID: a3c9e5d17b64
Revises: f2b8c4d1a937
Create Date: 2026-11-11 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c9e5d17b64'
down_revision: Union[str, Sequence[str], None] = 'f2b8c4d1a937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega las dos columnas (admiten vacío, siempre) y la clave foránea del usuario que quitó la fuente."""
    op.add_column('T_Documento', sa.Column('CF_Fecha_baja', sa.DateTime(), nullable=True))
    op.add_column('T_Documento', sa.Column('CN_Id_usuario_baja', sa.String(length=20), nullable=True))
    op.create_foreign_key(
        'FK_T_Documento_Usuario_baja', 'T_Documento', 'T_Usuario', ['CN_Id_usuario_baja'], ['CN_Id_usuario'])


def downgrade() -> None:
    """No pierde información (RN-01): falla si hay documentos con baja."""
    op.execute("""
        IF EXISTS (SELECT 1 FROM [T_Documento] WHERE [CF_Fecha_baja] IS NOT NULL)
            THROW 50001, 'No se pueden quitar las columnas: hay documentos con baja lógica.', 1;
    """)
    op.drop_constraint('FK_T_Documento_Usuario_baja', 'T_Documento', type_='foreignkey')
    op.drop_column('T_Documento', 'CN_Id_usuario_baja')
    op.drop_column('T_Documento', 'CF_Fecha_baja')
