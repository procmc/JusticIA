"""
Fase 3 - Estado del arte y seleccion preliminar de HTR/ICR.

Muestra el embudo de decision: candidatos investigados -> filtro de
politica (origen no chino) -> comparacion de los 3 candidatos viables ->
recomendacion preliminar para el Ciclo 1 de la Fase 4.

No es una decision final (esa se toma en el Ciclo 1 con pruebas
empiricas reales, ver doc 22) - esta es la recomendacion basada en
investigacion de la Fase 3 (doc 17).

Ejecutar: python seleccion_htr_fase3.py
Output: output/seleccion_htr_fase3.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python

print("Generando diagrama: Seleccion HTR Fase 3...")

with Diagram(
    "ServIA - Fase 3: Estado del Arte HTR/ICR\nEmbudo de decision (investigacion, no prueba empirica)",
    show=False,
    direction="TB",
    filename="output/seleccion_htr_fase3",
    outformat="png",
    graph_attr={
        "fontsize": "13",
        "bgcolor": "white",
        "pad": "1.0",
        "splines": "spline",
        "nodesep": "1.0",
        "ranksep": "1.3"
    }
):
    with Cluster("Candidatos investigados", graph_attr={
        "bgcolor": "#f3f4f6", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        trocr = Python("TrOCR\n(Microsoft, EE.UU.)")
        donut = Python("Donut\n(Naver Clova, Corea)")
        surya = Python("Surya\n(Datalab, EE.UU.)")
        paddle = Python("PaddleOCR\n(Baidu, China)")
        qwen = Python("Qwen2.5-VL\n(Alibaba, China)")

    filtro = Python("Filtro de politica institucional\n'Nada de origen chino'\n(sin evaluar desempeño)")

    with Cluster("Comparados por merito (los 3 no chinos)", graph_attr={
        "bgcolor": "#eff6ff", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        comp_trocr = Python("TrOCR\n\n+ Mas checkpoints ya\n  entrenados/afinados\n+ Transformer bien\n  documentado")
        comp_donut = Python("Donut\n\n+ Entiende layout+contenido\n- Necesita afinado propio\n  por dominio")
        comp_surya = Python("Surya\n\n+ +90 idiomas, buen en\n  documentos mixtos\n- Manuscrito sigue siendo\n  su punto debil")

    recomendacion = Python("Recomendacion preliminar\n(no es decision final)\n\nEmpezar Ciclo 1 con TrOCR\nDonut/Surya como respaldo")

    for c in [trocr, donut, surya]:
        c >> Edge(color="#16a34a", style="dashed") >> filtro
    for c in [paddle, qwen]:
        c >> Edge(color="#dc2626", style="dashed", label="  excluido  ") >> filtro

    filtro >> Edge(color="#2563eb") >> comp_trocr
    filtro >> Edge(color="#2563eb") >> comp_donut
    filtro >> Edge(color="#2563eb") >> comp_surya

    comp_trocr >> Edge(color="#7c3aed", label="  elegido para\n  empezar  ") >> recomendacion
    comp_donut >> Edge(color="#9ca3af", style="dashed", label="  respaldo  ") >> recomendacion
    comp_surya >> Edge(color="#9ca3af", style="dashed", label="  respaldo  ") >> recomendacion

print("Diagrama generado: output/seleccion_htr_fase3.png")
