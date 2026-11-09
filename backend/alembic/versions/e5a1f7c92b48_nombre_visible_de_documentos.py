"""nombre visible de documentos

Spec 009b (RN-01.100, RF-21.100): agrega T_Documento.CT_Nombre_visible (NULL = se muestra el nombre interno; el archivo en
disco se sigue ubicando por CT_Nombre_archivo) y el tipo de acción 21 «Renombrar Documento de Notebook». No cambia los datos
existentes.

Revision ID: e5a1f7c92b48
Revises: d94c2a6e33a5
Create Date: 2026-11-06 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a1f7c92b48'
down_revision: Union[str, Sequence[str], None] = 'd94c2a6e33a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la columna CT_Nombre_visible (admite vacío, siempre) y suma el tipo de acción 21 solo si no existe."""
    op.add_column('T_Documento', sa.Column('CT_Nombre_visible', sa.String(length=500), nullable=True))
    op.execute("""
        SET IDENTITY_INSERT [T_Tipo_accion] ON;

        INSERT INTO [T_Tipo_accion] ([CN_Id_tipo_accion], [CT_Nombre_tipo_accion])
        SELECT v.id, v.nombre
        FROM (VALUES
            (21, N'Renombrar Documento de Notebook')
        ) AS v(id, nombre)
        WHERE NOT EXISTS (SELECT 1 FROM [T_Tipo_accion] t WHERE t.[CN_Id_tipo_accion] = v.id);

        SET IDENTITY_INSERT [T_Tipo_accion] OFF;
    """)


def downgrade() -> None:
    """No pierde información (RN-01): falla si hay nombres visibles o bitácora con el tipo 21."""
    op.execute("""
        IF EXISTS (SELECT 1 FROM [T_Documento] WHERE [CT_Nombre_visible] IS NOT NULL)
            THROW 50001, 'No se puede quitar la columna: hay documentos con nombre visible.', 1;
        IF EXISTS (SELECT 1 FROM [T_Bitacora] WHERE [CN_Id_tipo_accion] = 21)
            THROW 50002, 'No se puede quitar el tipo de acción 21: la bitácora tiene registros que lo usan.', 1;
        DELETE FROM [T_Tipo_accion] WHERE [CN_Id_tipo_accion] = 21;
    """)
    op.drop_column('T_Documento', 'CT_Nombre_visible')
