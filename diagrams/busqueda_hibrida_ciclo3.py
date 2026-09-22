"""
Busqueda hibrida en el chat general (doc 28, Fase 4 - Ciclo 3).

Conecta el filtro exacto de Qdrant (ya existia en el codigo pero nadie lo
usaba desde el chat general) con la busqueda semantica: si la pregunta
menciona un numero de expediente exacto, se detecta por regex y se combina
con la similitud vectorial, con una red de seguridad que reintenta sin
filtro si el expediente detectado no tiene datos.

De paso se corrigio un bug real: 5 lecturas de metadata en
qdrant_backend.py usaban la key "numero_expediente" en vez de
"metadata.numero_expediente", asi que el filtro nunca habia devuelto nada
desde que se escribio.

Ejecutar: python busqueda_hibrida_ciclo3.py
Output: output/busqueda_hibrida_ciclo3.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.generic.database import SQL

print("Generando diagrama: Busqueda hibrida (Ciclo 3)...")

with Diagram(
    "ServIA - Busqueda Hibrida en el Chat General (doc 28, Ciclo 3)\nSemantica + filtro exacto de Qdrant, con red de seguridad si el expediente detectado no tiene datos",
    show=False,
    direction="LR",
    filename="output/busqueda_hibrida_ciclo3",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "0.9",
        "ranksep": "1.2"
    }
):
    pregunta = Python("Pregunta del chat general\n(sin expediente fijado)")

    with Cluster("retriever.py: _get_general_documents()", graph_attr={
        "bgcolor": "#eff6ff", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        deteccion = Python("extraer_expediente_de_texto()\nregex sobre texto libre\n(expediente_validator.py)")

    with Cluster("search_strategies.py: search_with_fallback()", graph_attr={
        "bgcolor": "#f0fdf4", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        hibrida = Python("Semantica + filtro exacto\n(expediente_filter pasado\na los 3 niveles de fallback)")
        semantica = Python("Solo semantica\n(sin filtro)")

    with Cluster("qdrant_backend.py: search_by_text()", graph_attr={
        "bgcolor": "#fdf4ff", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        qdrant = SQL("Filter(key=\n\"metadata.numero_expediente\")\n+ similitud vectorial")

    red_seguridad = Python("Red de seguridad:\n0 resultados con filtro\n-> reintenta SIN filtro")

    pregunta >> Edge(color="#2563eb") >> deteccion
    deteccion >> Edge(color="#16a34a", label="  expediente detectado  ") >> hibrida
    deteccion >> Edge(color="#6b7280", label="  no detectado  ") >> semantica
    hibrida >> Edge(color="#a855f7") >> qdrant
    semantica >> Edge(color="#a855f7", style="dashed") >> qdrant
    hibrida >> Edge(color="#dc2626", style="dashed", label="  0 resultados  ") >> red_seguridad
    red_seguridad >> Edge(color="#6b7280", style="dashed") >> semantica

print("Diagrama generado: output/busqueda_hibrida_ciclo3.png")
