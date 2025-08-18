# 1) Crear y activar venv (opcional pero recomendado)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
#source .venv/bin/activate

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) (Opcional) Exportar variables si no usaste .env
# set MILVUS_URI=...
# set MILVUS_TOKEN=...
# etc.

# 4) Correr FastAPI
uvicorn main:app --reload
