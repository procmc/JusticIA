import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# Configuración Milvus (Base de datos vectorial)
MILVUS_URI = os.getenv("MILVUS_URI")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

# Configuración Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# Configuración SQL Server
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER")

# URLs de conexión para SQL Server
DATABASE_URL = f"mssql+pyodbc://{SQL_SERVER_USER}:{quote_plus(SQL_SERVER_PASSWORD)}@{SQL_SERVER_HOST}:{SQL_SERVER_PORT}/{SQL_SERVER_DATABASE}?driver={quote_plus(SQL_SERVER_DRIVER)}&TrustServerCertificate=yes"

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

if not MILVUS_URI or not MILVUS_TOKEN:
    raise RuntimeError("Configura MILVUS_URI y MILVUS_TOKEN (.env o variables de entorno).")
