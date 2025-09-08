#!/bin/bash

# Verificar e instalar dependencias
if ! command -v java &> /dev/null; then
    echo "Instalando Java..."
    sudo dnf install -y java-17-openjdk-devel
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Instalando FFmpeg..."
    sudo dnf install -y ffmpeg
fi

# Configurar entorno Python con Python 3.11
if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual con Python 3.11..."
    # Intentar usar python3.11 primero, luego python3
    if command -v python3.11 &> /dev/null; then
        python3.11 -m venv .venv
        VENV_EXIT_CODE=$?
    elif command -v python3 &> /dev/null; then
        # Verificar que sea Python 3.11
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [ "$PYTHON_VERSION" = "3.11" ]; then
            python3 -m venv .venv
            VENV_EXIT_CODE=$?
        else
            echo "Advertencia: Python 3.11 no encontrado, usando Python3 disponible ($PYTHON_VERSION)"
            python3 -m venv .venv
            VENV_EXIT_CODE=$?
        fi
    else
        echo "Error: Python3 no esta instalado"
        exit 1
    fi
    
    # Verificar si la creacion del entorno fue exitosa
    if [ $VENV_EXIT_CODE -ne 0 ]; then
        echo "Error: No se pudo crear el entorno virtual"
        exit 1
    fi
else
    echo "Entorno virtual ya existe."
fi

echo "Activando entorno virtual..."
source .venv/bin/activate

# Verificar activacion
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Entorno virtual activado correctamente"
    echo "Ruta del entorno: $VIRTUAL_ENV"
else
    echo "Advertencia: El entorno virtual puede no estar activado correctamente"
fi

echo "Version de Python: $(python --version)"

# Actualizar pip primero
echo "Actualizando pip..."
python -m pip install --upgrade pip

# Instalar dependencias esenciales primero
echo "Instalando dependencias esenciales..."
python -m pip install wheel setuptools

# Instalar dependencias principales
echo "Instalando todas las dependencias..."
python -m pip install -r requirements.txt

# Ejecutar servidor
uvicorn main:app --reload
