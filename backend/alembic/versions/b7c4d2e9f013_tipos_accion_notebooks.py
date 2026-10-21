"""tipos_accion_notebooks

Agrega al catálogo T_Tipo_accion los tres tipos de acción de la spec 004b (RF-21.34):
16 «Crear Notebook», 17 «Quitar Documento de Notebook» y 18 «Gestionar Conversación».
Solo inserta datos del catálogo: ninguna tabla cambia de esquema.

Revision ID: b7c4d2e9f013
Revises: a1b2c3d4e5f6
Create Date: 2026-10-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b7c4d2e9f013'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Inserta los tipos 16, 17 y 18 si todavía no existen."""
    op.execute("""
        SET IDENTITY_INSERT [T_Tipo_accion] ON;

        INSERT INTO [T_Tipo_accion] ([CN_Id_tipo_accion], [CT_Nombre_tipo_accion])
        SELECT v.id, v.nombre
        FROM (VALUES
            (16, N'Crear Notebook'),
            (17, N'Quitar Documento de Notebook'),
            (18, N'Gestionar Conversación')
        ) AS v(id, nombre)
        WHERE NOT EXISTS (SELECT 1 FROM [T_Tipo_accion] t WHERE t.[CN_Id_tipo_accion] = v.id);

        SET IDENTITY_INSERT [T_Tipo_accion] OFF;
    """)


def downgrade() -> None:
    """Borra los tipos 16, 17 y 18 solo si ninguna fila de la bitácora los usa (RN-01: no se borran registros)."""
    op.execute("""
        IF EXISTS (SELECT 1 FROM [T_Bitacora] WHERE [CN_Id_tipo_accion] IN (16, 17, 18))
            THROW 50001, 'No se pueden quitar los tipos de acción 16 a 18: la bitácora tiene registros que los usan.', 1;
        DELETE FROM [T_Tipo_accion] WHERE [CN_Id_tipo_accion] IN (16, 17, 18);
    """)
