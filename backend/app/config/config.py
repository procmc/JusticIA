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
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

# Configuración Whisper para transcripción de audio
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

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
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", ""))

if not MILVUS_URI or not MILVUS_TOKEN:
    raise RuntimeError("Configura MILVUS_URI y MILVUS_TOKEN (.env o variables de entorno).")
