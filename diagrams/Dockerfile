# Dockerfile para servicio de generación de diagramas
# Base: Python 3.11 slim con Graphviz

FROM python:3.11-slim

# Metadata
LABEL maintainer="ServIA Team"
LABEL description="Servicio de generación de diagramas de arquitectura"

# Instalar Graphviz (requerido por Python Diagrams)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    graphviz \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /diagrams

# Copiar requirements y instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar scripts de generación
COPY *.py ./

# Crear directorio de salida
RUN mkdir -p output icons

# Verificar instalación de Graphviz
RUN dot -V

# Comando por defecto: generar todos los diagramas
CMD ["python", "generate_all.py"]
