"""
Integracion del servicio HTR (doc 22, Fase 4 - Ciclo 1, segunda mitad).

Muestra el patron cliente-servidor (calcado de Tika) por el que el backend
consume el reconocimiento de manuscrito, y el mecanismo de intercambio de
GPU por inactividad que permite compartir 8 GB de VRAM entre el servidor
HTR y Ollama sin que ninguno expulse al otro.

Ejecutar: python integracion_htr_ciclo1.py
Output: output/integracion_htr_ciclo1.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.compute import Server
from diagrams.custom import Custom
from diagrams.generic.storage import Storage

print("Generando diagrama: Integracion del servicio HTR (Ciclo 1)...")

with Diagram(
    "ServIA - Integracion del Servicio HTR (doc 22, Ciclo 1)\nPatron cliente-servidor (igual que Tika) + GPU compartida por intercambio de inactividad",
    show=False,
    direction="LR",
    filename="output/integracion_htr_ciclo1",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "0.9",
        "ranksep": "1.1"
    }
):
    with Cluster("backend (sin GPU)", graph_attr={
        "bgcolor": "#eff6ff", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        procesador = Python("document_processor.py\n(rutea .jpg/.png/.tif/.bmp)")
        cliente = Python("htr_service.py\n(cliente HTTP,\ncalcado de tika_service.py)")
        procesador >> Edge(color="#2563eb") >> cliente

    with Cluster("servidor-htr (contenedor propio, con GPU)", graph_attr={
        "bgcolor": "#fdf4ff", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        api = Server("FastAPI\nGET /salud\nPOST /htr")
        with Cluster("Intercambio por inactividad", graph_attr={
            "bgcolor": "#fae8ff", "penwidth": "1", "style": "rounded,dashed",
            "margin": "18", "pad": "0.4"
        }):
            modelo_gpu = Storage("trocr-large-handwritten\nEN GPU (~2.1 GB)")
            modelo_cpu = Storage("trocr-large-handwritten\nEN CPU (ocioso)")
            modelo_gpu >> Edge(color="#a855f7", label="  >120s sin peticiones  ", style="dashed") >> modelo_cpu
            modelo_cpu >> Edge(color="#16a34a", label="  siguiente peticion  ") >> modelo_gpu

        api >> Edge(color="#a855f7") >> modelo_gpu

    with Cluster("GPU compartida (RTX 3070, 8 GB)", graph_attr={
        "bgcolor": "#f3f4f6", "penwidth": "1", "style": "rounded",
        "margin": "20", "pad": "0.4"
    }):
        ollama = Custom("Ollama\n(OLLAMA_KEEP_ALIVE,\nmismo patron de intercambio)", "/diagrams/icons/ollama.png")

    cliente >> Edge(color="#2563eb", label="  HTTP: imagen en bytes  ") >> api
    api >> Edge(color="#2563eb", label="  texto reconocido  ") >> cliente
    modelo_gpu >> Edge(color="#6b7280", style="dotted", label="  compite por la misma VRAM,\n  nunca al mismo tiempo  ") >> ollama

print("Diagrama generado: output/integracion_htr_ciclo1.png")
