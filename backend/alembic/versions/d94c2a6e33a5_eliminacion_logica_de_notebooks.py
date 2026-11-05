"""eliminacion logica de notebooks

Spec 009 (RN-01.80, RF-21.80): agrega T_Notebook.CF_Fecha_eliminacion (NULL = activo; no se borra la fila) y los tipos
de acción 19 «Renombrar Notebook» y 20 «Eliminar Notebook». No cambia los datos existentes.

Revision ID: d94c2a6e33a5
Revises: b7c4d2e9f013
Create Date: 2026-11-05 16:35:48.556032

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd94c2a6e33a5'
down_revision: Union[str, Sequence[str], None] = 'b7c4d2e9f013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega la columna CF_Fecha_eliminacion (admite vacío, siempre) y suma los tipos de acción 19 y 20 solo si no existen."""
    op.add_column('T_Notebook', sa.Column('CF_Fecha_eliminacion', sa.DateTime(), nullable=True))
    op.execute("""
        SET IDENTITY_INSERT [T_Tipo_accion] ON;

        INSERT INTO [T_Tipo_accion] ([CN_Id_tipo_accion], [CT_Nombre_tipo_accion])
        SELECT v.id, v.nombre
        FROM (VALUES
            (19, N'Renombrar Notebook'),
            (20, N'Eliminar Notebook')
        ) AS v(id, nombre)
        WHERE NOT EXISTS (SELECT 1 FROM [T_Tipo_accion] t WHERE t.[CN_Id_tipo_accion] = v.id);

        SET IDENTITY_INSERT [T_Tipo_accion] OFF;
    """)


def downgrade() -> None:
    """No pierde información (RN-01): falla si hay notebooks eliminados o bitácora con los tipos 19 y 20."""
    op.execute("""
        IF EXISTS (SELECT 1 FROM [T_Notebook] WHERE [CF_Fecha_eliminacion] IS NOT NULL)
            THROW 50001, 'No se puede quitar la columna: hay notebooks con fecha de eliminación.', 1;
        IF EXISTS (SELECT 1 FROM [T_Bitacora] WHERE [CN_Id_tipo_accion] IN (19, 20))
            THROW 50002, 'No se pueden quitar los tipos de acción 19 y 20: la bitácora tiene registros que los usan.', 1;
        DELETE FROM [T_Tipo_accion] WHERE [CN_Id_tipo_accion] IN (19, 20);
    """)
    op.drop_column('T_Notebook', 'CF_Fecha_eliminacion')
