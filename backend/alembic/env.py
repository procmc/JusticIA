from logging.config import fileConfig
import os
from dotenv import load_dotenv

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Cargar variables de entorno
load_dotenv()

# Importar nuestros modelos para que Alembic los detecte
from app.db.models import Base, T_Usuario, T_Expediente, T_Documento, T_Bitacora, T_Rol, T_Estado, T_Estado_procesamiento, T_Tipo_accion, T_Usuario_Expediente, T_Expediente_Documento

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Construir URL de la base de datos desde variables de entorno
    sql_server_host = os.getenv("SQL_SERVER_HOST")
    sql_server_port = os.getenv("SQL_SERVER_PORT", "1433")
    sql_server_database = os.getenv("SQL_SERVER_DATABASE")
    sql_server_user = os.getenv("SQL_SERVER_USER")
    sql_server_password = os.getenv("SQL_SERVER_PASSWORD")
    sql_server_driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    
    database_url = f"mssql+pyodbc://{sql_server_user}:{sql_server_password}@{sql_server_host}:{sql_server_port}/{sql_server_database}?driver={sql_server_driver}&TrustServerCertificate=yes"
    
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Construir URL de la base de datos desde variables de entorno
    sql_server_host = os.getenv("SQL_SERVER_HOST")
    sql_server_port = os.getenv("SQL_SERVER_PORT", "1433")
    sql_server_database = os.getenv("SQL_SERVER_DATABASE")
    sql_server_user = os.getenv("SQL_SERVER_USER")
    sql_server_password = os.getenv("SQL_SERVER_PASSWORD")
    sql_server_driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    
    database_url = f"mssql+pyodbc://{sql_server_user}:{sql_server_password}@{sql_server_host}:{sql_server_port}/{sql_server_database}?driver={sql_server_driver}&TrustServerCertificate=yes"
    
    # Sobrescribir la configuración con nuestra URL
    config.set_main_option("sqlalchemy.url", database_url)
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
