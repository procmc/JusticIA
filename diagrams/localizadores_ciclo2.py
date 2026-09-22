"""
Los dos localizadores de renglones (doc 25, Fase 4 - Ciclo 2, hallazgo 2).

Compara el enfoque original (umbral global de Otsu, segmentacion.py) contra
el detector entrenado que lo reemplazo en produccion el 17/09/2026
(deteccion_aprendida.py, DBNet de docTR). La eleccion se decide con
evaluar_hoja.py, que mide el pipeline COMPLETO (localizador + TrOCR +
union de renglones), no un componente aislado.

Ejecutar: python localizadores_ciclo2.py
Output: output/localizadores_ciclo2.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage

print("Generando diagrama: Localizadores de renglones (Ciclo 2)...")

with Diagram(
    "ServIA - Ciclo 2: Dos localizadores de renglones (doc 25)\nHTR_LOCALIZADOR=doctr es el valor de despliegue (docker-compose.yml) - decidido midiendo, no por preferencia",
    show=False,
    direction="LR",
    filename="output/localizadores_ciclo2",
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
    foto = Storage("Foto de pagina completa\n(page 4000x3000, sin recortar)")

    with Cluster("HTR_LOCALIZADOR=otsu   segmentacion.py", graph_attr={
        "bgcolor": "#fef2f2", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        otsu = Python("Umbral global de Otsu\n(+ papel, encuadernado,\nfranjas, autocorrelacion)")
        otsu_res = Storage("CER 0.4507\n1 de 9 parrafos")
        otsu >> Edge(color="#dc2626") >> otsu_res

    with Cluster("HTR_LOCALIZADOR=doctr   deteccion_aprendida.py  (produccion)", graph_attr={
        "bgcolor": "#f0fdf4", "penwidth": "2", "style": "rounded",
        "margin": "25", "pad": "0.5"
    }):
        doctr = Python("Detector ENTRENADO\n(DBNet/ResNet-50, docTR)\n+ numeracion = corte de parrafo")
        doctr_res = Storage("CER 0.3248\n9 de 9 parrafos")
        doctr >> Edge(color="#16a34a") >> doctr_res

    referencia = Storage("Recorte manual (referencia)\nCER 0.2480")

    foto >> Edge(color="#6b7280") >> otsu
    foto >> Edge(color="#6b7280") >> doctr
    otsu_res >> Edge(color="#dc2626", style="dashed", label="  -28% relativo  ") >> doctr_res
    doctr_res >> Edge(color="#6b7280", style="dotted", label="  brecha restante:\n  ubicacion (2/8) + LoRA  ") >> referencia

print("Diagrama generado: output/localizadores_ciclo2.png")
