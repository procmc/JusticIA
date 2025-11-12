# Diagramas de Arquitectura - JusticIA

Generacion automatica de diagramas de arquitectura del sistema usando Python Diagrams.

## Setup y Ejecucion

### Opcion 1: Docker (Recomendado)

No necesitas instalar Graphviz ni Python localmente.

```bash
cd diagrams
chmod +x generate_diagrams.sh
./generate_diagrams.sh
```

**Generar diagrama individual:**
```bash
./generate_diagrams.sh nivel_2b_rag
```

### Opcion 2: Ejecucion Local (Requiere instalaciones)

#### 1. Instalar Graphviz

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install graphviz
```

**Red Hat/CentOS:**
```bash
sudo yum install graphviz
```

**macOS:**
```bash
brew install graphviz
```

#### 2. Instalar dependencias Python

```bash
cd diagrams
pip install -r requirements.txt
```

#### 3. Verificar instalacion

```bash
dot -V  # Debe mostrar la version de Graphviz
python --version  # Python 3.8+
```

## Estructura de Archivos

```
diagrams/
├── README.md                    # Esta guía
├── requirements.txt             # Dependencias Python
├── generate_all.py              # Genera TODOS los diagramas
├── nivel_0_contexto.py          # Contexto del sistema
├── nivel_1_contenedores.py      # Arquitectura de alto nivel
├── nivel_2a_ingesta.py          # Módulo de ingesta (detalle)
├── nivel_2b_rag.py              # Módulo RAG/Chat (detalle)
├── nivel_2c_similares.py        # Búsqueda de similares (detalle)
├── nivel_3_flujo_datos.py       # Flujo de datos end-to-end
├── nivel_4_deployment.py        # Vista de despliegue Docker
├── icons/                       # Iconos personalizados (opcional)
└── output/                      # Diagramas generados (PNG)
    ├── nivel_0_contexto.png
    ├── nivel_1_contenedores.png
    └── ...
```

## Generar Diagramas

### Con Docker (Recomendado):

```bash
# Generar todos
./generate_diagrams.sh

# Generar uno especifico
./generate_diagrams.sh nivel_2b_rag
```

### Sin Docker (Requiere Graphviz instalado):

```bash
# Generar todos
python generate_all.py

# Generar uno especifico
python nivel_0_contexto.py
python nivel_1_contenedores.py
python nivel_2a_ingesta.py
python nivel_2b_rag.py
python nivel_2c_similares.py
python nivel_3_flujo_datos.py
python nivel_4_deployment.py
```

### Comando Docker directo:

```bash
# Generar todos
docker-compose --profile tools run --rm diagrams python generate_all.py

# Generar uno especifico
docker-compose --profile tools run --rm diagrams python nivel_2b_rag.py

# Modo interactivo (debugging)
docker-compose --profile tools run --rm diagrams bash
```

### Ver diagramas generados:

```bash
# Linux
xdg-open output/nivel_1_contenedores.png

# macOS
open output/nivel_1_contenedores.png
```

## Editar Diagramas

Cada archivo `.py` es independiente y editable:

1. **Abrir el archivo** que quieres modificar (ej: `nivel_1_contenedores.py`)
2. **Editar** colores, etiquetas, conexiones, etc.
3. **Ejecutar** el archivo para regenerar:
   ```powershell
   python nivel_1_contenedores.py
   ```
4. **Ver resultado** en `output/`

### Ejemplo de personalización:

```python
# Cambiar dirección del diagrama
direction="TB"  # Top to Bottom
direction="LR"  # Left to Right
direction="BT"  # Bottom to Top
direction="RL"  # Right to Left

# Cambiar formato de salida
outformat="png"  # PNG (recomendado)
outformat="svg"  # SVG (escalable)
outformat="pdf"  # PDF
outformat="jpg"  # JPEG

# Cambiar colores de edges
Edge(color="blue")
Edge(color="red")
Edge(color="green")
Edge(color="orange")
Edge(color="purple")

# Agregar etiquetas
Edge(label="HTTPS")
Edge(label="REST API")
Edge(label="gRPC")
```

## Niveles de Diagramas

### Nivel 0 - Contexto del Sistema
- Vista mas alta
- Usuarios y sistemas externos
- Proposito: Entender el "que" y "quienes"

### Nivel 1 - Contenedores
- Arquitectura de alto nivel
- Todos los servicios/aplicaciones
- Tecnologias especificas
- Proposito: Entender el "como" general

### Nivel 2A/B/C - Componentes
- Zoom en modulos especificos
- Componentes internos
- Flujos detallados
- Proposito: Entender implementacion

### Nivel 3 - Flujo de Datos
- Seguir un dato/evento
- Transformaciones
- Estados
- Proposito: Debugging y optimizacion

### Nivel 4 - Deployment
- Infraestructura fisica
- Contenedores Docker
- Recursos (CPU/RAM)
- Proposito: Operaciones y escalabilidad

## Tips y Personalizacion

### Usar iconos personalizados:
```python
from diagrams.custom import Custom

ollama = Custom("Ollama\nGPT-OSS", "./icons/ollama.png")
milvus = Custom("Milvus\nVector DB", "./icons/milvus.png")
```

### Agrupar elementos:
```python
with Cluster("Nombre del Cluster"):
    componente1 = Server("...")
    componente2 = Server("...")
```

### Colores para Clusters:
```python
graph_attr={
    "bgcolor": "lightblue"
}
```

### Multiples conexiones:
```python
# Una a una
a >> b
b >> c

# En cadena
a >> b >> c >> d

# Multiple destinos
a >> [b, c, d]
```

## Recursos

- Documentacion oficial: https://diagrams.mingrammer.com/
- Ejemplos: https://diagrams.mingrammer.com/docs/getting-started/examples
- Iconos disponibles: https://diagrams.mingrammer.com/docs/nodes/aws
- Graphviz docs: https://graphviz.org/documentation/

## Troubleshooting

### Error: "Graphviz not found"
```bash
# Verificar instalacion
dot -V

# Reinstalar si es necesario
sudo apt-get install --reinstall graphviz
```

### Error: "No module named diagrams"
```bash
pip install diagrams
```

### Los iconos custom no se encuentran
```python
# Asegurar rutas relativas desde el archivo .py
./icons/ollama.png  # Correcto
icons/ollama.png    # Podria fallar
```

### Diagrama no se ve bien
- Cambiar `direction` (TB, LR, BT, RL)
- Agregar/quitar Clusters
- Simplificar conexiones
- Usar `show=True` para ver en navegador automaticamente

## Presentacion Recomendada

Para presentar a arquitectos tecnicos:

1. Nivel 0 (5 min) - Contexto general
2. Nivel 1 (10 min) - Arquitectura completa
3. Nivel 2A (7 min) - Ingesta detallada
4. Nivel 2B (7 min) - RAG detallado
5. Nivel 2C (6 min) - Busqueda similares
6. Nivel 3 (5 min) - Seguir un documento
7. Nivel 4 (5 min) - Deployment e infraestructura
8. Q&A (15 min)

## Notas

- Los archivos `.py` se versionan en Git
- Los archivos `.png` en `output/` son opcionales (se pueden regenerar)
- Mantener iconos en `icons/` versionados
- Actualizar diagramas cuando cambies arquitectura
