"""
Script maestro para generar todos los diagramas de arquitectura.

Este script ejecuta todos los diagramas en secuencia:
- Contexto del Sistema
- Procesamiento de Documentos Legales
- Consultas con IA (RAG)
- Búsqueda de Similitud de Casos
- Stack Tecnológico y Dependencias
- Arquitectura de Despliegue

Uso:
    python generate_all.py
    
Requiere:
    - Graphviz instalado en el sistema
    - Paquetes Python: diagrams, graphviz
    
Output:
    Todos los diagramas en formato PNG en la carpeta output/
"""

import sys
import time
from pathlib import Path

def run_diagram(script_name: str, description: str):
    """Ejecuta un script de diagrama y reporta el resultado."""
    print(f"\n{'='*70}")
    print(f"Generando: {description}")
    print(f"{'='*70}")
    
    try:
        start_time = time.time()
        
        # Importar y ejecutar el módulo
        module_name = script_name.replace('.py', '')
        __import__(module_name)
        
        elapsed = time.time() - start_time
        print(f"[OK] Completado en {elapsed:.2f}s")
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    """Función principal para generar todos los diagramas."""
    
    print("""
===============================================================================
                GENERADOR DE DIAGRAMAS DE ARQUITECTURA - JusticIA
                     Sistema de Asistencia Judicial con IA
===============================================================================
    """)
    
    # Verificar que existe la carpeta output
    output_dir = Path("output")
    if not output_dir.exists():
        print("[INFO] Carpeta 'output' no existe. Creandola...")
        output_dir.mkdir(parents=True)
    
    # Lista de diagramas a generar
    diagrams = [
        ("contexto_sistema.py", "Contexto del Sistema"),
        ("stack_tecnologico.py", "Stack Tecnológico y Dependencias"),
        ("arquitectura_despliegue.py", "Arquitectura de Despliegue"),
        ("procesamiento_documentos.py", "Procesamiento de Documentos Legales"),
        ("consultas_ia_rag.py", "Consultas con IA (RAG)"),
        ("busqueda_similitud.py", "Búsqueda de Similitud de Casos"),
        ("ingesta_simple.py", "Ingesta de Documentos (Flujo General)"),
        ("rag_simple.py", "Consultas con IA RAG (Flujo General)"),
        ("busqueda_simple.py", "Búsqueda de Similitud (Flujo General)"),
    ]
    
    start_total = time.time()
    results = []
    
    # Generar cada diagrama
    for script, description in diagrams:
        success = run_diagram(script, description)
        results.append((description, success))
    
    # Resumen final
    total_elapsed = time.time() - start_total
    successful = sum(1 for _, success in results if success)
    failed = len(results) - successful
    
    print(f"\n{'='*70}")
    print(f"RESUMEN DE GENERACION")
    print(f"{'='*70}")
    print(f"Total de diagramas: {len(results)}")
    print(f"[OK] Exitosos: {successful}")
    print(f"[ERROR] Fallidos: {failed}")
    print(f"Tiempo total: {total_elapsed:.2f}s")
    print(f"{'='*70}")
    
    # Detalle de resultados
    print("\nDetalle:")
    for description, success in results:
        status = "[OK]" if success else "[ERROR]"
        print(f"  {status} {description}")
    
    if failed > 0:
        print("\n[ADVERTENCIA] Algunos diagramas fallaron. Revisa los errores arriba.")
        print("[INFO] Asegurate de que Graphviz este instalado correctamente.")
        return 1
    else:
        print(f"\n[SUCCESS] Todos los diagramas generados exitosamente!")
        print(f"Ubicacion: {output_dir.absolute()}")
        print("\nProximos pasos:")
        print("   1. Revisa los diagramas en la carpeta output/")
        print("   2. Edita los scripts individuales si necesitas ajustar algo")
        print("   3. Vuelve a ejecutar este script o scripts individuales")
        print("   4. Usa los diagramas en tu presentacion tecnica")
        return 0

if __name__ == "__main__":
    sys.exit(main())
