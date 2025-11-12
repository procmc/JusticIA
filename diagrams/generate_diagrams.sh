#!/bin/bash
# Script para generar diagramas usando Docker
# Uso: ./generate_diagrams.sh [all|nivel_0|nivel_1|nivel_2a|nivel_2b|nivel_2c|nivel_3|nivel_4]

set -e

DIAGRAM=$1

echo ""
echo "==============================================================================="
echo "              GENERADOR DE DIAGRAMAS - JusticIA (Docker)"
echo "==============================================================================="
echo ""

# Crear directorio output si no existe
mkdir -p output

if [ -z "$DIAGRAM" ] || [ "$DIAGRAM" == "all" ]; then
    echo "Generando TODOS los diagramas..."
    docker-compose --profile tools run --rm diagrams python generate_all.py
else
    echo "Generando diagrama: ${DIAGRAM}"
    docker-compose --profile tools run --rm diagrams python "${DIAGRAM}.py"
fi

echo ""
echo "[SUCCESS] Diagramas generados exitosamente!"
echo "Ubicacion: $(pwd)/output/"
echo ""
ls -lh output/*.png 2>/dev/null || echo "[INFO] No se encontraron diagramas PNG"
