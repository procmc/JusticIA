"""
Contexto del Sistema ServIA
Vista de alto nivel: las personas que usan el sistema y los servicios con los
que se comunica. SQL Server, Qdrant y Ollama corren en local (Docker) junto a
ServIA; ningun dato ni consulta sale a servicios de IA en la nube. El servidor
de correo es el unico servicio fuera del equipo.

Ejecutar: python contexto_sistema.py
Output: output/contexto_sistema.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.custom import Custom
from diagrams.programming.language import Python


print("Generando diagrama: Contexto del Sistema...")

with Diagram(
    "ServIA - Asistente de IA Gubernamental\nContexto del Sistema",
    show=False,
    direction="TB",
    filename="output/contexto_sistema",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.5",
        "splines": "spline",
        "nodesep": "2.0",
        "ranksep": "2.0"
    }
):
    # Actores - Paleta azul claro
    with Cluster("Usuarios", graph_attr={
        "bgcolor": "#e3f2fd",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        usuario = User("Usuario Gubernamental")
        admin = User("Administrador")

    # Sistema principal
    sistema = Python("ServIA\n\nAsistente de IA\nGubernamental")

    # Servicios de apoyo - Paleta morado claro
    with Cluster("Servicios de Apoyo", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        sql_server = Custom("SQL Server\n(Local)\n\nDatos transaccionales", "/diagrams/icons/SQL Server.png")
        qdrant = Custom("Qdrant\n(Local)\n\nBúsqueda vectorial", "/diagrams/icons/Qdrant.png")
        ollama = Custom("Ollama\n(Local)\n\nGeneración IA", "/diagrams/icons/ollama.png")
        correo = Custom("Servidor de correo\n(Gmail, SMTP)\n\nContraseñas y códigos", "/diagrams/icons/Gmail.png")

    # Relaciones - Usuarios
    usuario >> Edge(label="  Consulta documentos  \n  Busca casos similares  \n  Usa notebooks  ", color="#2563eb", fontsize="11") >> sistema
    admin >> Edge(label="  Administra sistema  ", color="#7c3aed", fontsize="11") >> sistema

    # Relaciones - Servicios de apoyo
    sistema >> Edge(label="  Almacena documentos  \n  y metadatos  ", color="#0891b2", fontsize="11") >> sql_server
    sistema >> Edge(label="  Búsqueda semántica  \n  de temas  ", color="#9333ea", fontsize="11") >> qdrant
    sistema >> Edge(label="  Generación de  \n  respuestas  ", color="#8b5cf6", fontsize="11") >> ollama
    sistema >> Edge(label="  Envía contraseñas  \n  y códigos  ", color="#059669", fontsize="11") >> correo

print("Diagrama generado: output/contexto_sistema.png")
