"""resultados de estudio

Spec 010 (RF-14.120, RN-01.120, RF-21.120): crea la tabla T_Resultado_Estudio (lo que el panel «Estudio» guarda en un notebook;
la baja es lógica, con CF_Fecha_eliminacion) y los tipos de acción 22 «Generar Resultado de Estudio», 23 «Guardar Nota» y
24 «Quitar Resultado de Estudio». No toca ninguna tabla ni dato existentes.

Revision ID: f2b8c4d1a937
Revises: e5a1f7c92b48
Create Date: 2026-11-09 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b8c4d1a937'
down_revision: Union[str, Sequence[str], None] = 'e5a1f7c92b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla (vacía) y suma los tipos de acción 22, 23 y 24 solo si no existen."""
    op.create_table(
        'T_Resultado_Estudio',
        sa.Column('CN_Id_resultado', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('CN_Id_notebook', sa.BigInteger(), nullable=False),
        sa.Column('CN_Id_usuario', sa.String(length=20), nullable=False),
        sa.Column('CT_Tipo', sa.String(length=20), nullable=False),
        sa.Column('CT_Titulo', sa.Unicode(length=200), nullable=False),
        sa.Column('CT_Contenido', sa.UnicodeText(), nullable=False),
        sa.Column('CT_Fuentes', sa.UnicodeText(), nullable=False),
        sa.Column('CF_Fecha_creacion', sa.DateTime(), nullable=False),
        sa.Column('CF_Fecha_eliminacion', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['CN_Id_notebook'], ['T_Notebook.CN_Id_notebook']),
        sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario']),
        sa.PrimaryKeyConstraint('CN_Id_resultado'),
    )
    op.create_index('ix_T_Resultado_Estudio_CN_Id_notebook', 'T_Resultado_Estudio', ['CN_Id_notebook'])
    op.execute("""
        SET IDENTITY_INSERT [T_Tipo_accion] ON;

        INSERT INTO [T_Tipo_accion] ([CN_Id_tipo_accion], [CT_Nombre_tipo_accion])
        SELECT v.id, v.nombre
        FROM (VALUES
            (22, N'Generar Resultado de Estudio'),
            (23, N'Guardar Nota'),
            (24, N'Quitar Resultado de Estudio')
        ) AS v(id, nombre)
        WHERE NOT EXISTS (SELECT 1 FROM [T_Tipo_accion] t WHERE t.[CN_Id_tipo_accion] = v.id);

        SET IDENTITY_INSERT [T_Tipo_accion] OFF;
    """)


def downgrade() -> None:
    """No pierde información (RN-01): falla si hay resultados guardados o bitácora con los tipos 22 a 24."""
    op.execute("""
        IF EXISTS (SELECT 1 FROM [T_Resultado_Estudio])
            THROW 50001, 'No se puede quitar la tabla: hay resultados de estudio guardados.', 1;
        IF EXISTS (SELECT 1 FROM [T_Bitacora] WHERE [CN_Id_tipo_accion] IN (22, 23, 24))
            THROW 50002, 'No se pueden quitar los tipos de acción 22 a 24: la bitácora tiene registros que los usan.', 1;
        DELETE FROM [T_Tipo_accion] WHERE [CN_Id_tipo_accion] IN (22, 23, 24);
    """)
    op.drop_index('ix_T_Resultado_Estudio_CN_Id_notebook', table_name='T_Resultado_Estudio')
    op.drop_table('T_Resultado_Estudio')
