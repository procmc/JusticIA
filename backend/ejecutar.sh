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

# Configurar entorno Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ejecutar servidor
uvicorn main:app --reload
