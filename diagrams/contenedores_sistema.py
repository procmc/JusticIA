"""
Contenedores del Sistema ServIA (C4 nivel 2)
Muestra las piezas que componen ServIA y como se comunican: la aplicacion web,
la API, el worker de procesamiento, los servicios de extraccion de texto y de
IA local, y los almacenes de datos. Todo corre en local con Docker Compose; el
servidor de correo es lo unico externo.

Ejecutar: python contenedores_sistema.py
Output: output/contenedores_sistema.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.onprem.queue import Celery
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import Fastapi
from diagrams.custom import Custom


print("Generando diagrama: Contenedores del Sistema...")

CLUSTER_AZUL = {"bgcolor": "#e3f2fd", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}
CLUSTER_VERDE = {"bgcolor": "#e8f5e9", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}
CLUSTER_MORADO = {"bgcolor": "#f3e5f5", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}
CLUSTER_NARANJA = {"bgcolor": "#fff3e0", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}
CLUSTER_GRIS = {"bgcolor": "#eceff1", "penwidth": "2", "style": "rounded", "margin": "30", "pad": "0.6"}

with Diagram(
    "ServIA - Asistente de IA Gubernamental\nContenedores del Sistema",
    show=False,
    direction="TB",
    filename="output/contenedores_sistema",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "0.4",
        "splines": "spline",
        "nodesep": "0.8",
        "ranksep": "1.5"
    }
):
    # Actores - Paleta azul claro
    with Cluster("Usuarios", graph_attr=CLUSTER_AZUL):
        usuario = User("Usuario Gubernamental")
        admin = User("Administrador")

    # Nucleo de ServIA - Paleta verde claro
    with Cluster("ServIA (Docker Compose)", graph_attr=CLUSTER_VERDE):
        web = Custom("Aplicación Web\nNext.js 15\n\nInterfaz de usuario", "/diagrams/icons/nextjs.png")
        api = Fastapi("API Backend\nFastAPI\n\nOrquesta las consultas")
        worker = Celery("Worker\nCelery\n\nProcesa archivos")

    # Procesamiento de documentos e IA local - Paleta morado claro
    with Cluster("Procesamiento e IA Local", graph_attr=CLUSTER_MORADO):
        tika = Custom("Apache Tika\nTesseract OCR\n\nExtracción de texto", "/diagrams/icons/tika.svg.png")
        htr = Custom("docTR + TrOCR\n(GPU compartida)\n\nTexto en imágenes", "/diagrams/icons/docTR.png")
        ollama = Custom("Ollama\nllama3.1:8b\n\nGeneración IA", "/diagrams/icons/ollama.png")

    # Almacenes de datos - Paleta naranja claro
    with Cluster("Datos y Almacenamiento", graph_attr=CLUSTER_NARANJA):
        sql_server = Custom("SQL Server 2022\n\nDatos transaccionales", "/diagrams/icons/SQL Server.png")
        qdrant = Custom("Qdrant\n\nBúsqueda vectorial", "/diagrams/icons/Qdrant.png")
        redis = Redis("Redis 7\n\nCola y progreso")
        archivos = Custom("Carpeta uploads\n\nArchivos originales", "/diagrams/icons/Archivos_originales.png")

    # Sistema externo - Paleta gris
    with Cluster("Servicios Externos", graph_attr=CLUSTER_GRIS):
        correo = Custom("Servidor de correo\n(Gmail, SMTP)\n\nContraseñas y códigos", "/diagrams/icons/Gmail.png")

    # Usuarios -> aplicacion web
    usuario >> Edge(label="  Usa (HTTPS)  ", color="#2563eb", fontsize="11") >> web
    admin >> Edge(label="  Usa (HTTPS)  ", color="#7c3aed", fontsize="11") >> web

    # Nucleo
    web >> Edge(label="  Llama a la API  ", color="#059669", fontsize="11", minlen="0", weight="30") >> api
    api >> Edge(label="  Encola archivos  \n  (vía Redis)  ", color="#059669", fontsize="11", minlen="0", weight="30") >> worker

    # Procesamiento e IA
    worker >> Edge(label="  Extrae texto  ", color="#9333ea", fontsize="11") >> tika
    worker >> Edge(label="  Reconoce texto  \n  en imágenes  ", color="#9333ea", fontsize="11") >> htr
    api >> Edge(label="  Genera respuestas  ", color="#8b5cf6", fontsize="11") >> ollama

    # Datos
    worker >> Edge(label="  Cola y progreso  ", color="#ea580c", fontsize="11") >> redis
    api >> Edge(label="  Lee y escribe  ", color="#ea580c", fontsize="11") >> sql_server
    worker >> Edge(label="  Indexa fragmentos  ", color="#ea580c", fontsize="11") >> qdrant
    api >> Edge(label="  Guarda archivos  ", color="#ea580c", fontsize="11") >> archivos

    # Correo
    api >> Edge(label="  Envía contraseñas  \n  y códigos  ", color="#546e7a", fontsize="11") >> correo

print("Diagrama generado: output/contenedores_sistema.png")
