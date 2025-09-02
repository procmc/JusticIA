from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

# Base para los modelos SQLAlchemy
Base = declarative_base()

# Motor de SQLAlchemy con validación de conexión
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Cambiar a True para ver las consultas SQL
        pool_pre_ping=True,
        pool_recycle=3600
    )
    
    # Probar conexión al inicializar
    with engine.connect() as conn:
        conn.execute("SELECT 1")
    
    print("CONEXIÓN A SQL SERVER EXITOSA")
    logger.info("Conexión a SQL Server exitosa")

except Exception as e:
    print(f"ERROR CONECTANDO A SQL SERVER: {e}")
    logger.error(f"Error conectando a SQL Server: {e}")
    engine = None

# SessionLocal para crear sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Dependency para obtener la sesión de base de datos
def get_db():
    """Dependency que proporciona una sesión de base de datos."""
    if not engine:
        raise Exception("Base de datos no disponible. Revisa la configuración.")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de base de datos: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

# Función para crear todas las tablas (cuando tengas modelos)
def create_tables():
    """Crea todas las tablas definidas en los modelos"""
    if not engine:
        logger.error("No se pueden crear tablas: motor de BD no disponible")
        return False
        
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas exitosamente")
        return True
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        return False
