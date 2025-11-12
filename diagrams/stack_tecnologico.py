"""
Stack Tecnológico - JusticIA
Vista detallada de componentes y dependencias por contenedor.

Ejecutar: python stack_tecnologico.py
Output: output/stack_tecnologico.png
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.container import Docker
from diagrams.programming.framework import React, Fastapi
from diagrams.programming.language import Python, Javascript, Nodejs
from diagrams.onprem.database import Mssql
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.compute import Server
from diagrams.custom import Custom


print("Generando diagrama: Stack Tecnológico...")

with Diagram(
    "JusticIA - Stack Tecnológico\nComponentes y Dependencias por Contenedor",
    show=False,
    direction="TB",
    filename="output/stack_tecnologico",
    outformat="png",
    graph_attr={
        "fontsize": "12",
        "bgcolor": "white",
        "ranksep": "1.5",
        "nodesep": "1.8",
        "pad": "1.5",
        "splines": "spline"
    }
):
    
    # ========== FRONTEND ==========
    with Cluster("Frontend Container", graph_attr={
        "bgcolor": "#E3F2FD",
        "penwidth": "3",
        "style": "rounded",
        "margin": "40",
        "pad": "0.8"
    }):
        with Cluster("Runtime", graph_attr={"bgcolor": "#BBDEFB", "style": "rounded", "margin": "25", "pad": "0.8"}):
            frontend_runtime = Nodejs("Node.js 20 Alpine")
        
        with Cluster("Framework", graph_attr={"bgcolor": "#90CAF9", "style": "rounded", "margin": "25", "pad": "0.8"}):
            nextjs = Custom("Next.js 15\n\nReact 18\nReact DOM\nSSR + SSG", "/diagrams/icons/nextjs.png")
        
        with Cluster("Build Tools", graph_attr={"bgcolor": "#64B5F6", "style": "rounded", "margin": "25", "pad": "0.8"}):
            frontend_tools = Javascript("npm / pnpm\n\nTailwind CSS\nPostCSS\nESLint")
        
        frontend_runtime >> Edge(color="#1976D2", style="solid") >> nextjs
        nextjs >> Edge(color="#1976D2", style="dashed") >> frontend_tools
    
    # ========== BACKEND API ==========
    with Cluster("Backend API Container", graph_attr={
        "bgcolor": "#F3E5F5",
        "penwidth": "3",
        "style": "rounded",
        "margin": "40",
        "pad": "0.8"
    }):
        with Cluster("Runtime & System", graph_attr={"bgcolor": "#E1BEE7", "style": "rounded", "margin": "25", "pad": "0.8"}):
            backend_runtime = Python("Python 3.11\n\nUbuntu 22.04\nvenv")
            backend_system = Custom("System Deps\n\nffmpeg\ncurl\nbuild-essential\nca-certificates", "/diagrams/icons/ffmpeg.png")
        
        with Cluster("Database Drivers", graph_attr={"bgcolor": "#CE93D8", "style": "rounded", "margin": "25", "pad": "0.8"}):
            backend_drivers = Mssql("ODBC Driver 18\n\nSQL Server\npyodbc\nsqlalchemy")
        
        with Cluster("Framework & Libraries", graph_attr={"bgcolor": "#BA68C8", "style": "rounded", "margin": "25", "pad": "0.8"}):
            backend_framework = Fastapi("FastAPI 0.116\n\nUvicorn\nPydantic\nPython-Jose (JWT)\nbcrypt")
        
        with Cluster("AI/ML Stack", graph_attr={"bgcolor": "#AB47BC", "style": "rounded", "margin": "25", "pad": "0.8"}):
            backend_ai = Custom("Embeddings Model\n\nBGE-M3-ES-Legal\nSentence Transformers\nPyTorch\n~3GB modelo", "/diagrams/icons/bge.jpeg")
        
        backend_runtime >> Edge(color="#7B1FA2", style="solid") >> backend_framework
        backend_runtime >> Edge(color="#7B1FA2", style="solid") >> backend_system
        backend_framework >> Edge(color="#7B1FA2", style="dashed") >> backend_drivers
        backend_framework >> Edge(color="#7B1FA2", style="dashed") >> backend_ai
    
    # ========== CELERY WORKER ==========
    with Cluster("Celery Worker Container", graph_attr={
        "bgcolor": "#FCE4EC",
        "penwidth": "3",
        "style": "rounded",
        "margin": "40",
        "pad": "0.8"
    }):
        with Cluster("Runtime & System", graph_attr={"bgcolor": "#F8BBD0", "style": "rounded", "margin": "25", "pad": "0.8"}):
            celery_runtime = Python("Python 3.11\n\nUbuntu 22.04\nvenv")
            celery_system = Custom("System Deps\n\nffmpeg (audio)\ncurl\nbuild-essential\nODBC Driver 18", "/diagrams/icons/ffmpeg.png")
        
        with Cluster("Task Queue", graph_attr={"bgcolor": "#F48FB1", "style": "rounded", "margin": "25", "pad": "0.8"}):
            celery_framework = Python("Celery 5.3\n\nPrefork pool\nRedis broker\nkombu")
        
        with Cluster("Processing Libraries", graph_attr={"bgcolor": "#F06292", "style": "rounded", "margin": "25", "pad": "0.8"}):
            celery_processing = Custom("Faster-Whisper\n\nCTranslate2\nPydub (audio)\nTika client\nLangChain", "/diagrams/icons/langchain.png")
        
        with Cluster("AI/ML Stack", graph_attr={"bgcolor": "#EC407A", "style": "rounded", "margin": "25", "pad": "0.8"}):
            celery_ai = Custom("Embeddings Model\n\nBGE-M3-ES-Legal\nSentence Transformers\nPyTorch\n~3GB modelo", "/diagrams/icons/bge.jpeg")
        
        celery_runtime >> Edge(color="#C2185B", style="solid") >> celery_framework
        celery_runtime >> Edge(color="#C2185B", style="solid") >> celery_system
        celery_framework >> Edge(color="#C2185B", style="dashed") >> celery_processing
        celery_framework >> Edge(color="#C2185B", style="dashed") >> celery_ai
    
    # ========== TIKA SERVER ==========
    with Cluster("Apache Tika Container", graph_attr={
        "bgcolor": "#E8F5E9",
        "penwidth": "3",
        "style": "rounded",
        "margin": "40",
        "pad": "0.8"
    }):
        with Cluster("Runtime", graph_attr={"bgcolor": "#C8E6C9", "style": "rounded", "margin": "25", "pad": "0.8"}):
            tika_runtime = Python("Java 17 JRE\n\nOpenJDK\nUbuntu 22.04")
        
        with Cluster("Tika Framework", graph_attr={"bgcolor": "#A5D6A7", "style": "rounded", "margin": "25", "pad": "0.8"}):
            tika_framework = Custom("Apache Tika 2.8.0\n\nServer Standard\ntika-config.xml\n15min timeout", "/diagrams/icons/tika.svg.png")
        
        with Cluster("OCR & Document Processing", graph_attr={"bgcolor": "#81C784", "style": "rounded", "margin": "25", "pad": "0.8"}):
            tika_ocr = Custom("Tesseract OCR\n\nEspañol + Inglés\nleptonica\nPoppler-utils\nImageMagick\nGhostscript", "/diagrams/icons/Tesseract_OCR.png")
        
        tika_runtime >> Edge(color="#388E3C", style="solid") >> tika_framework
        tika_framework >> Edge(color="#388E3C", style="dashed") >> tika_ocr
    
    # ========== REDIS ==========
    with Cluster("Redis Container", graph_attr={
        "bgcolor": "#FFF3E0",
        "penwidth": "3",
        "style": "rounded",
        "margin": "40",
        "pad": "0.8"
    }):
        with Cluster("Cache & Queue System", graph_attr={"bgcolor": "#FFE0B2", "style": "rounded", "margin": "25", "pad": "0.8"}):
            redis_server = Redis("Redis 7 Alpine\n\nMaxmemory: 1GB\nPolicy: allkeys-lru\nPersistence: RDB\nAOF disabled")
        
        with Cluster("Use Cases", graph_attr={"bgcolor": "#FFCC80", "style": "rounded", "margin": "25", "pad": "0.8"}):
            redis_usage = Python("Broker Celery\nResult backend\nSesiones chat\nCache queries")
        
        redis_server >> Edge(color="#F57C00", style="dashed") >> redis_usage

print("Diagrama generado: output/stack_tecnologico.png")
