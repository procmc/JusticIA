import os
from dotenv import load_dotenv

load_dotenv()

MILVUS_URI = os.getenv("MILVUS_URI")
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN")
MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "default")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "justicia_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Configuración Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct")

if not MILVUS_URI or not MILVUS_TOKEN:
    raise RuntimeError("Configura MILVUS_URI y MILVUS_TOKEN (.env o variables de entorno).")
