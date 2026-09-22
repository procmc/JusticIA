"""
Aclaracion de arquitectura (doc 21): monolito modular, no microservicios.

Compara lo que afirma el readme.md heredado ("arquitectura de
microservicios") contra lo que muestra el codigo real (994 archivos
analizados de la rama main): un solo backend con todos los dominios
juntos, rodeado de infraestructura de terceros (no logica de negocio
propia).

Ejecutar: python arquitectura_monolito_vs_microservicios.py
Output: output/arquitectura_monolito_vs_microservicios.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.onprem.database import Mssql
from diagrams.generic.database import SQL
from diagrams.custom import Custom
from diagrams.onprem.inmemory import Redis

print("Generando diagrama: Monolito vs Microservicios...")

with Diagram(
    "ServIA - Aclaracion de Arquitectura (doc 21)\nSI es un sistema distribuido, pero NO son microservicios (994 archivos analizados)",
    show=False,
    direction="TB",
    filename="output/arquitectura_monolito_vs_microservicios",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "1.0",
        "ranksep": "1.1"
    }
):
    with Cluster("AFIRMA EL README: \"arquitectura de microservicios\"\n(NO existe asi en el codigo)", graph_attr={
        "bgcolor": "#fef2f2", "penwidth": "2", "style": "rounded,dashed",
        "margin": "30", "pad": "0.6", "fontsize": "13"
    }):
        s_auth = Python("Servicio Auth\n(propio main.py)")
        s_ingesta = Python("Servicio Ingesta\n(propio main.py)")
        s_rag = Python("Servicio RAG\n(propio main.py)")
        s_bitacora = Python("Servicio Bitacora\n(propio main.py)")

    with Cluster("MUESTRA EL CODIGO REAL: monolito modular", graph_attr={
        "bgcolor": "#f0fdf4", "penwidth": "2", "style": "rounded",
        "margin": "30", "pad": "0.6", "fontsize": "13"
    }):
        with Cluster("backend (UN solo main.py, UN solo contenedor)", graph_attr={
            "bgcolor": "#dcfce7", "penwidth": "2", "style": "rounded",
            "margin": "20", "pad": "0.4"
        }):
            dominios = Python("auth + ingesta + RAG +\nbusqueda_similares + bitacora\n\n(todos los dominios juntos,\nrutes/ -> services/ -> repositories/)")

        celery = Python("celery-worker\n\n(mismo codigo que\nbackend, no logica propia)")

        with Cluster("Infraestructura de terceros (NO logica de negocio propia)", graph_attr={
            "bgcolor": "#f3f4f6", "penwidth": "1", "style": "rounded",
            "margin": "20", "pad": "0.4"
        }):
            sql = Mssql("SQL Server")
            qdrant = SQL("Qdrant")
            redis = Redis("Redis")
            ollama = Custom("Ollama", "/diagrams/icons/ollama.png")
            tika = Custom("Tika", "/diagrams/icons/tika.svg.png")

        dominios >> Edge(color="#16a34a", label="  mismo codigo  ") >> celery
        dominios >> Edge(color="#6b7280") >> sql
        dominios >> Edge(color="#6b7280") >> qdrant
        dominios >> Edge(color="#6b7280") >> redis
        dominios >> Edge(color="#6b7280") >> ollama
        dominios >> Edge(color="#6b7280") >> tika

print("Diagrama generado: output/arquitectura_monolito_vs_microservicios.png")
