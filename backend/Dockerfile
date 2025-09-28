
# Dockerfile para el backend usando Ubuntu minimal y Python 3.11

FROM ubuntu:22.04

# Instalar dependencias del sistema y Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-distutils python3.11-dev python3-pip \
    openjdk-17-jre-headless ffmpeg git curl build-essential \
    ca-certificates gnupg apt-transport-https unzip htop \
    && rm -rf /var/lib/apt/lists/*

# Instalar ODBC Driver 18 for SQL Server
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

# Copiar solo los archivos necesarios al contenedor
COPY requirements.txt /app/
COPY . /app/

# Crear el entorno virtual y verificar el binario
RUN python3.11 -m venv /app/.venv \
    && /app/.venv/bin/pip install --upgrade pip setuptools wheel \
    && /app/.venv/bin/pip install -r /app/requirements.txt \
    && ls -l /app/.venv/bin/python \
    && /app/.venv/bin/python --version

ENV PATH="/app/.venv/bin:$PATH"

# Exponer el puerto del backend
EXPOSE 8000

# Comando para iniciar el backend
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
