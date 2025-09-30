
# Dockerfile para el backend usando Ubuntu minimal y Python 3.11

FROM ubuntu:22.04

# Instalar dependencias del sistema y Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-distutils python3.11-dev python3-pip \
    ffmpeg git curl build-essential \
    ca-certificates gnupg apt-transport-https unzip htop \
    && rm -rf /var/lib/apt/lists/*

# Instalar ODBC Driver 18 for SQL Server
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar solo requirements.txt primero para aprovechar la caché
COPY requirements.txt /app/

# Crear el entorno virtual fuera de /app para evitar sobrescritura por volumen
RUN python3.11 -m venv /venv \
    && /venv/bin/pip install --upgrade pip setuptools wheel \
    && /venv/bin/pip install -r /app/requirements.txt \
    && ls -l /venv/bin/python \
    && /venv/bin/python --version

ENV PATH="/venv/bin:$PATH"


# Copiar el resto del código fuente (esto invalida la caché solo si el código cambia)
COPY . /app/

# Exponer el puerto del backend
EXPOSE 8000

# Comando para iniciar el backend
CMD ["/venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
