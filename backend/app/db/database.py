from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.config import DATABASE_URL
import logging
import time

logger = logging.getLogger(__name__)

# Base para los modelos SQLAlchemy
Base = declarative_base()

# Reintentos de conexión al arrancar: SQL Server puede tardar más que este
# contenedor en estar listo para aceptar conexiones (pasa sobre todo cuando
# se levantan los 8 contenedores juntos). Sin esto, un solo intento fallido
# dejaba engine/SessionLocal en None para siempre, sin reintentar.
MAX_REINTENTOS_DB = 10
ESPERA_ENTRE_REINTENTOS = 3  # segundos

# Motor de SQLAlchemy con pool aumentado para concurrencia
engine = None
intentos = 0
while intentos < MAX_REINTENTOS_DB and engine is None:
    intentos += 1
    try:
        engine_candidato = create_engine(
            DATABASE_URL,
            echo=False,  # Cambiar a True para ver las consultas SQL
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=20,          # Base de 20 conexiones (era 5 por defecto)
            max_overflow=40,       # Hasta 40 adicionales (era 10 por defecto)
            pool_timeout=60,       # Timeout más largo: 60 segundos
            pool_reset_on_return='commit'  # Limpiar conexiones al devolverlas
        )

        # Probar conexión al inicializar
        with engine_candidato.connect() as conn:
            conn.execute(text("SELECT 1"))

        engine = engine_candidato
        print(f"CONEXIÓN A SQL SERVER EXITOSA (intento {intentos}/{MAX_REINTENTOS_DB})")
        logger.info(f"Conexión a SQL Server exitosa (intento {intentos}/{MAX_REINTENTOS_DB})")

    except Exception as e:
        print(f"Intento {intentos}/{MAX_REINTENTOS_DB} fallido conectando a SQL Server: {e}")
        logger.warning(f"Intento {intentos}/{MAX_REINTENTOS_DB} fallido conectando a SQL Server: {e}")
        if intentos < MAX_REINTENTOS_DB:
            time.sleep(ESPERA_ENTRE_REINTENTOS)

if engine is None:
    print(f"ERROR CONECTANDO A SQL SERVER: se agotaron los {MAX_REINTENTOS_DB} intentos")
    logger.error(f"Error conectando a SQL Server: se agotaron los {MAX_REINTENTOS_DB} intentos")

# SessionLocal para crear sesiones de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine else None

# Dependency para obtener la sesión de base de datos
def get_db():
    """Dependency que proporciona una sesión de base de datos."""
    if not engine or not SessionLocal:
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
