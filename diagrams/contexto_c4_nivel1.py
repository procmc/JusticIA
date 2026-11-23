"""
Contexto del Sistema ServIA - C4 nivel 1 (version estricta)
Solo las personas, ServIA como una sola caja y el unico sistema externo (el
servidor de correo). Es la version que acompana a la seccion 4 del documento
"Arquitectura C4 - ServIA"; la vista con los servicios locales esta en
contexto_sistema.py.

Ejecutar: python contexto_c4_nivel1.py
Output: output/contexto_c4_nivel1.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.custom import Custom
from diagrams.programming.language import Python


print("Generando diagrama: Contexto C4 nivel 1...")

with Diagram(
    "ServIA - Asistente de IA Gubernamental\nContexto del Sistema",
    show=False,
    direction="TB",
    filename="output/contexto_c4_nivel1",
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
    with Cluster("Usuarios", graph_attr={
        "bgcolor": "#e3f2fd",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        usuario = User("Usuario Gubernamental")
        admin = User("Administrador")

    # group="eje": ServIA y el correo en la misma vertical
    sistema = Python("ServIA\n\nAsistente de IA\nGubernamental", group="eje")

    with Cluster("Servicios Externos", graph_attr={
        "bgcolor": "#f3e5f5",
        "penwidth": "2",
        "style": "rounded",
        "margin": "30",
        "pad": "0.6"
    }):
        correo = Custom("Servidor de correo\n(Gmail, SMTP)\n\nContraseñas y códigos", "/diagrams/icons/Gmail.png", group="eje")

    usuario >> Edge(label="  Consulta documentos  \n  Busca casos similares  \n  Usa notebooks  ", color="#2563eb", fontsize="11") >> sistema
    admin >> Edge(label="  Administra sistema  ", color="#7c3aed", fontsize="11") >> sistema
    sistema >> Edge(label="  Envía contraseñas  \n  y códigos  ", color="#0891b2", fontsize="11") >> correo

    # Aristas invisibles: solo centran a ServIA entre los dos actores
    usuario >> Edge(style="invis") >> correo
    admin >> Edge(style="invis") >> correo

print("Diagrama generado: output/contexto_c4_nivel1.png")
