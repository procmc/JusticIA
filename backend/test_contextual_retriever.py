#!/usr/bin/env python3
"""
Test del retriever contextual mejorado
Verifica que consultas específicas obtengan información completa del expediente
"""
import asyncio
import sys
import os

# Agregar el directorio backend al path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.services.RAG.retriever import DynamicJusticIARetriever

async def test_contextual_retriever():
    print("🧪 TESTING RETRIEVER CONTEXTUAL MEJORADO")
    
    # Simular contexto de conversación que incluye expediente de hostigamiento laboral
    context = """
    Usuario: Tienes conocimiento sobre casos de hostigamiento laboral?
    Asistente: Sí, el expediente 2022-063557-6597-LA trata específicamente de hostigamiento laboral.
    Usuario: Puedes darme un resumen más largo
    Asistente: [Resumen del expediente 2022-063557-6597-LA]
    """
    
    # Crear retriever con contexto
    retriever = DynamicJusticIARetriever(
        conversation_context=context,
        top_k=20
    )
    
    # Test 1: Consulta de bitácora (ya funcionaba)
    print("\n1️⃣ TESTING: Consulta de bitácora...")
    bitacora_docs = await retriever._aget_relevant_documents('¿Cuál es la bitácora del caso?')
    print(f"   Documentos encontrados: {len(bitacora_docs)}")
    if bitacora_docs:
        print(f"   Primera bitácora: {bitacora_docs[0].page_content[:100]}...")
    
    # Test 2: Consulta sobre nombres (nuevo)
    print("\n2️⃣ TESTING: Consulta sobre Ana Fernández...")
    nombre_docs = await retriever._aget_relevant_documents('¿Quién es Ana Fernández?')
    print(f"   Documentos encontrados: {len(nombre_docs)}")
    if nombre_docs:
        print(f"   Información sobre Ana: {nombre_docs[0].page_content[:200]}...")
    
    # Test 3: Consulta sobre actora (nuevo)
    print("\n3️⃣ TESTING: Consulta sobre la actora...")
    actora_docs = await retriever._aget_relevant_documents('¿Cómo se llama la actora?')
    print(f"   Documentos encontrados: {len(actora_docs)}")
    if actora_docs:
        print(f"   Información de actora: {actora_docs[0].page_content[:200]}...")
    
    # Test 4: Consulta sobre antecedentes (nuevo)
    print("\n4️⃣ TESTING: Consulta sobre antecedentes...")
    antecedentes_docs = await retriever._aget_relevant_documents('¿Cuáles son los antecedentes del caso?')
    print(f"   Documentos encontrados: {len(antecedentes_docs)}")
    if antecedentes_docs:
        print(f"   Antecedentes: {antecedentes_docs[0].page_content[:200]}...")
    
    # Test 5: Consulta sobre pruebas (nuevo)
    print("\n5️⃣ TESTING: Consulta sobre pruebas...")
    pruebas_docs = await retriever._aget_relevant_documents('¿Cuáles son las pruebas del caso?')
    print(f"   Documentos encontrados: {len(pruebas_docs)}")
    if pruebas_docs:
        print(f"   Pruebas: {pruebas_docs[0].page_content[:200]}...")
    
    print("\n✅ TESTING COMPLETO")
    
    # Resumen de resultados
    print(f"\n📊 RESUMEN:")
    print(f"   Bitácora: {len(bitacora_docs)} docs")
    print(f"   Ana Fernández: {len(nombre_docs)} docs")
    print(f"   Actora: {len(actora_docs)} docs")
    print(f"   Antecedentes: {len(antecedentes_docs)} docs")
    print(f"   Pruebas: {len(pruebas_docs)} docs")

if __name__ == "__main__":
    asyncio.run(test_contextual_retriever())