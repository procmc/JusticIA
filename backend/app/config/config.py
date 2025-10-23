import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Configuración Milvus (Base de datos vectorial)
MILVUS_URI = os.getenv("MILVUS_URI", "")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-mpnet-base-v2")

# Configuración Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Configuración Whisper para transcripción de audio
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Configuración Redis para Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Configuración Tika para procesamiento de documentos
TIKA_SERVER_URL = os.getenv("TIKA_SERVER_URL", "http://localhost:9998")

# Configuración SQL Server
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE", "")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER", "")

# URLs de conexión para SQL Server
DATABASE_URL = f"mssql+pyodbc://{SQL_SERVER_USER}:{quote_plus(SQL_SERVER_PASSWORD)}@{SQL_SERVER_HOST}:{SQL_SERVER_PORT}/{SQL_SERVER_DATABASE}?driver={quote_plus(SQL_SERVER_DRIVER)}&TrustServerCertificate=yes"

# Configuración JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
# Legacy: JWT_EXPIRE_HOURS (hours) kept for backward compatibility
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))
# Preferencia moderna: controlar expiración en minutos mediante ACCESS_TOKEN_EXPIRE_MINUTES
JWT_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(JWT_EXPIRE_HOURS * 60)))

# Configuración LLM
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_KEEP_ALIVE = os.getenv("LLM_KEEP_ALIVE", "10m")
LLM_REQUEST_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "600"))
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "2048"))
LLM_NUM_PREDICT = int(os.getenv("LLM_NUM_PREDICT", "1024"))
LLM_TOP_K = int(os.getenv("LLM_TOP_K", "40"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.95"))
LLM_REPEAT_PENALTY = float(os.getenv("LLM_REPEAT_PENALTY", "1.1"))

if not MILVUS_URI or not MILVUS_TOKEN:
    raise RuntimeError("Configura MILVUS_URI y MILVUS_TOKEN (.env o variables de entorno).")
