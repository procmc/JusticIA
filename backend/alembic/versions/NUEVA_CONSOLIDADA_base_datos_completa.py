"""Base de datos completa con estructura y datos iniciales consolidados

Revision ID: 001_base_completa
Revises: 
Create Date: 2025-10-17 22:00:00.000000

MIGRACIÓN CONSOLIDADA - Incluye:
1. Estructura completa de todas las tablas
2. Datos iniciales de catálogos (roles, estados, tipos de acción)
3. Cambios aplicados en migraciones previas:
   - Campos CF_Ultimo_acceso y CF_Fecha_creacion en T_Usuario
   - CN_Id_expediente nullable en T_Bitacora
4. Nuevos tipos de acción para módulos faltantes (RAG, archivos, auth completa)

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


# revision identifiers, used by Alembic.
revision: str = '001_base_completa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Crear estructura completa de base de datos con todos los datos iniciales.
    """
    
    # ============================================
    # PASO 1: CREAR TABLAS DE CATÁLOGO
    # ============================================
    
    # Tabla de estados de usuario
    op.create_table('T_Estado',
        sa.Column('CN_Id_estado', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre_estado', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('CN_Id_estado'),
        sa.UniqueConstraint('CT_Nombre_estado')
    )
    
    # Tabla de estados de procesamiento de documentos
    op.create_table('T_Estado_procesamiento',
        sa.Column('CN_Id_estado', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre_estado', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('CN_Id_estado'),
        sa.UniqueConstraint('CT_Nombre_estado')
    )
    
    # Tabla de roles
    op.create_table('T_Rol',
        sa.Column('CN_Id_rol', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre_rol', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('CN_Id_rol'),
        sa.UniqueConstraint('CT_Nombre_rol')
    )
    
    # Tabla de tipos de acción para bitácora
    op.create_table('T_Tipo_accion',
        sa.Column('CN_Id_tipo_accion', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre_tipo_accion', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('CN_Id_tipo_accion'),
        sa.UniqueConstraint('CT_Nombre_tipo_accion')
    )
    
    # ============================================
    # PASO 2: CREAR TABLAS PRINCIPALES
    # ============================================
    
    # Tabla de expedientes
    op.create_table('T_Expediente',
        sa.Column('CN_Id_expediente', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('CT_Num_expediente', sa.String(length=60), nullable=False),
        sa.Column('CF_Fecha_creacion', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('CN_Id_expediente'),
        sa.UniqueConstraint('CT_Num_expediente', name='uq_expediente_num')
    )
    
    # Tabla de documentos
    op.create_table('T_Documento',
        sa.Column('CN_Id_documento', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('CT_Nombre_archivo', sa.String(length=255), nullable=False),
        sa.Column('CT_Tipo_archivo', sa.String(length=50), nullable=False),
        sa.Column('CT_Ruta_archivo', sa.String(length=500), nullable=True),
        sa.Column('CF_Fecha_carga', sa.DateTime(), nullable=False),
        sa.Column('CN_Id_estado', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['CN_Id_estado'], ['T_Estado_procesamiento.CN_Id_estado'], ),
        sa.PrimaryKeyConstraint('CN_Id_documento')
    )
    
    # Tabla de usuarios (con campos adicionales consolidados)
    op.create_table('T_Usuario',
        sa.Column('CN_Id_usuario', sa.String(length=20), autoincrement=False, nullable=False),
        sa.Column('CT_Nombre_usuario', sa.String(length=50), nullable=False),
        sa.Column('CT_Nombre', sa.String(length=100), nullable=False),
        sa.Column('CT_Apellido_uno', sa.String(length=100), nullable=False),
        sa.Column('CT_Apellido_dos', sa.String(length=100), nullable=True),
        sa.Column('CT_Correo', sa.String(length=100), nullable=False),
        sa.Column('CT_Contrasenna', sa.String(length=255), nullable=False),
        sa.Column('CN_Id_rol', sa.Integer(), nullable=True),
        sa.Column('CN_Id_estado', sa.Integer(), nullable=True),
        # Campos agregados en migración c039f8f03469
        sa.Column('CF_Ultimo_acceso', sa.DateTime(), nullable=True),
        sa.Column('CF_Fecha_creacion', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['CN_Id_estado'], ['T_Estado.CN_Id_estado'], ),
        sa.ForeignKeyConstraint(['CN_Id_rol'], ['T_Rol.CN_Id_rol'], ),
        sa.PrimaryKeyConstraint('CN_Id_usuario'),
        sa.UniqueConstraint('CT_Correo', name='uq_usuario_correo'),
        sa.UniqueConstraint('CT_Nombre_usuario', name='uq_usuario_nombre')
    )
    
    # Tabla de bitácora (con CN_Id_expediente nullable desde el inicio)
    op.create_table('T_Bitacora',
        sa.Column('CN_Id_bitacora', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('CF_Fecha_hora', sa.DateTime(), nullable=False),
        sa.Column('CT_Texto', sa.Text(), nullable=False),
        sa.Column('CT_Informacion_adicional', sa.Text(), nullable=True),
        sa.Column('CN_Id_usuario', sa.String(length=20), nullable=False),
        sa.Column('CN_Id_tipo_accion', sa.Integer(), nullable=True),
        # Campo modificado en migración e5c8cac575b3 - ahora nullable desde el inicio
        sa.Column('CN_Id_expediente', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['CN_Id_expediente'], ['T_Expediente.CN_Id_expediente'], ),
        sa.ForeignKeyConstraint(['CN_Id_tipo_accion'], ['T_Tipo_accion.CN_Id_tipo_accion'], ),
        sa.ForeignKeyConstraint(['CN_Id_usuario'], ['T_Usuario.CN_Id_usuario'], ),
        sa.PrimaryKeyConstraint('CN_Id_bitacora')
    )
    
    # Tabla de relación expediente-documento
    op.create_table('T_Expediente_Documento',
        sa.Column('CN_Id_expediente', sa.BigInteger(), nullable=False),
        sa.Column('CN_Id_documento', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['CN_Id_documento'], ['T_Documento.CN_Id_documento'], ),
        sa.ForeignKeyConstraint(['CN_Id_expediente'], ['T_Expediente.CN_Id_expediente'], ),
        sa.PrimaryKeyConstraint('CN_Id_expediente', 'CN_Id_documento')
    )
    
    # ============================================
    # PASO 3: INSERTAR DATOS INICIALES
    # ============================================
    
    # Insertar estados de procesamiento de documentos
    op.execute("""
        INSERT INTO [T_Estado_procesamiento] ([CT_Nombre_estado]) VALUES 
        ('Pendiente'),
        ('Procesado'), 
        ('Error')
    """)
    
    # Insertar roles de usuario
    op.execute("""
        INSERT INTO [T_Rol] ([CT_Nombre_rol]) VALUES 
        ('Administrador'),
        ('Usuario Judicial')
    """)
    
    # Insertar estados de usuario
    op.execute("""
        INSERT INTO [T_Estado] ([CT_Nombre_estado]) VALUES 
        ('Activo'),
        ('Inactivo')
    """)
    
    # ============================================
    # PASO 4: INSERTAR TIPOS DE ACCIÓN COMPLETOS
    # ============================================
    # Incluye los 8 tipos originales + 7 nuevos tipos = 15 tipos totales
    
    op.execute("""
        SET IDENTITY_INSERT [T_Tipo_accion] ON;
        
        INSERT INTO [T_Tipo_accion] ([CN_Id_tipo_accion], [CT_Nombre_tipo_accion]) VALUES 
        (1, 'Búsqueda de Casos Similares'),
        (2, 'Carga de Documentos'),
        (3, 'Login'),
        (4, 'Logout'),
        (5, 'Cambio de Contraseña'),
        (6, 'Recuperación de Contraseña'),
        (7, 'Crear Usuario'),
        (8, 'Editar Usuario'),
        (9, 'Consultar Usuarios'),
        (10, 'Descargar Archivo'),
        (11, 'Listar Archivos'),
        (12, 'Consulta RAG'),
        (13, 'Generar Resumen'),
        (14, 'Consultar Bitácora'),
        (15, 'Exportar Bitácora');
        
        SET IDENTITY_INSERT [T_Tipo_accion] OFF;
    """)
    
    # ============================================
    # PASO 5: CREAR USUARIO ADMINISTRADOR POR DEFECTO
    # ============================================
    # Credenciales configurables desde .env
    # Variables: ADMIN_CEDULA, ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD
    #            ADMIN_NOMBRE, ADMIN_APELLIDO
    # ============================================
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Leer credenciales desde variables de entorno (con valores por defecto)
    admin_cedula = os.getenv('ADMIN_CEDULA', '000000000')
    admin_username = os.getenv('ADMIN_USERNAME', 'admin')
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@justicia.go.cr')
    admin_password = os.getenv('ADMIN_PASSWORD', 'Admin2025!')
    admin_nombre = os.getenv('ADMIN_NOMBRE', 'Administrador')
    admin_apellido = os.getenv('ADMIN_APELLIDO', 'Sistema')
    
    # Generar hash bcrypt de la contraseña
    contrasenna_hash = pwd_context.hash(admin_password)
    
    # Insertar usuario administrador
    # Rol: Administrador (ID 1), Estado: Activo (ID 1)
    op.execute(f"""
        INSERT INTO [T_Usuario] (
            [CN_Id_usuario],
            [CT_Nombre_usuario],
            [CT_Nombre],
            [CT_Apellido_uno],
            [CT_Apellido_dos],
            [CT_Correo],
            [CT_Contrasenna],
            [CN_Id_rol],
            [CN_Id_estado],
            [CF_Fecha_creacion]
        ) VALUES (
            '{admin_cedula}',
            '{admin_username}',
            '{admin_nombre}',
            '{admin_apellido}',
            NULL,
            '{admin_email}',
            '{contrasenna_hash}',
            1,
            1,
            GETDATE()
        )
    """)


def downgrade() -> None:
    """
    Eliminar toda la estructura de base de datos.
    ADVERTENCIA: Esto eliminará TODOS los datos.
    """
    
    # Leer cédula del admin desde .env para eliminar correctamente
    admin_cedula = os.getenv('ADMIN_CEDULA', '000000000')
    
    # Eliminar datos iniciales primero (en orden inverso)
    op.execute(f"DELETE FROM [T_Usuario] WHERE [CN_Id_usuario] = '{admin_cedula}'")
    op.execute("DELETE FROM [T_Tipo_accion]")
    op.execute("DELETE FROM [T_Estado]")
    op.execute("DELETE FROM [T_Rol]")
    op.execute("DELETE FROM [T_Estado_procesamiento]")
    
    # Eliminar tablas en orden inverso para respetar foreign keys
    op.drop_table('T_Expediente_Documento')
    op.drop_table('T_Bitacora')
    op.drop_table('T_Usuario')
    op.drop_table('T_Documento')
    op.drop_table('T_Tipo_accion')
    op.drop_table('T_Rol')
    op.drop_table('T_Expediente')
    op.drop_table('T_Estado_procesamiento')
    op.drop_table('T_Estado')
