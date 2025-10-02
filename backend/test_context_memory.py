#!/usr/bin/env python3
"""
Prueba del sistema de memoria de contexto mejorado
Simula el escenario reportado por el usuario
"""

import asyncio
import sys
import os

# Agregar el directorio backend al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.RAG.retriever import DynamicJusticIARetriever

async def test_context_memory():
    """Simula el escenario del usuario: hablar de hostigamiento laboral, cambiar a narcotráfico, volver a preguntar por detalles"""
    
    print("=" * 80)
    print("🧪 PRUEBA: MEMORIA DE CONTEXTO CON MÚLTIPLES EXPEDIENTES")
    print("=" * 80)
    
    # ESCENARIO 1: Conversación inicial sobre hostigamiento laboral
    print("\n🔵 ESCENARIO 1: Consulta inicial sobre hostigamiento laboral")
    context_inicial = ""
    retriever1 = DynamicJusticIARetriever(conversation_context=context_inicial)
    
    docs1 = await retriever1._aget_relevant_documents("Tienes conocimiento sobre un caso de hostigamiento laboral?")
    print(f"📄 Documentos encontrados: {len(docs1)}")
    if docs1:
        print(f"🔍 Primer documento: {docs1[0].page_content[:150]}...")
        if docs1[0].metadata.get('expediente_numero'):
            exp_encontrado = docs1[0].metadata['expediente_numero']
            print(f"📋 Expediente encontrado: {exp_encontrado}")
    
    # ESCENARIO 2: Obtener bitácora (contextual)
    print("\n🟢 ESCENARIO 2: Consulta contextual de bitácora")
    context_con_hostigamiento = "Usuario preguntó sobre expediente 2022-063557-6597-LA sobre hostigamiento laboral"
    retriever2 = DynamicJusticIARetriever(conversation_context=context_con_hostigamiento)
    
    docs2 = await retriever2._aget_relevant_documents("¿Cuál es la bitácora del caso?")
    print(f"📄 Documentos encontrados: {len(docs2)}")
    if docs2:
        print(f"🔍 Primer documento: {docs2[0].page_content[:150]}...")
        print(f"🧠 Expedientes en sesión: {retriever2.session_expedients}")
    
    # ESCENARIO 3: Cambio de tema a narcotráfico
    print("\n🟡 ESCENARIO 3: Cambio de tema a narcotráfico")
    context_con_ambos = """Usuario preguntó sobre expediente 2022-063557-6597-LA sobre hostigamiento laboral. 
    Luego preguntó sobre bitácora. Después preguntó sobre casos de narcotráfico. 
    Se mencionaron expedientes 2022-259949-3683-PN y 2024-487576-7239-PN"""
    
    retriever3 = DynamicJusticIARetriever(conversation_context=context_con_ambos)
    
    docs3 = await retriever3._aget_relevant_documents("Conoces casos de narcotrafico?")
    print(f"📄 Documentos encontrados: {len(docs3)}")
    print(f"🧠 Expedientes en sesión: {retriever3.session_expedients}")
    
    # ESCENARIO 4: Consulta específica sobre expediente mencionado anteriormente
    print("\n🔴 ESCENARIO 4: PROBLEMA ORIGINAL - Consulta sobre expediente específico mencionado antes")
    
    docs4 = await retriever3._aget_relevant_documents("Puedes darme mas información sobre 2024-487576-7239-PN")
    print(f"📄 Documentos encontrados: {len(docs4)}")
    if docs4:
        print(f"🔍 Primer documento: {docs4[0].page_content[:150]}...")
        print(f"📋 Expediente: {docs4[0].metadata.get('expediente_numero', 'No especificado')}")
    else:
        print("❌ NO SE ENCONTRARON DOCUMENTOS - AQUÍ ESTABA EL PROBLEMA")
    
    # ESCENARIO 5: Consulta sobre involucrados (debe usar memoria de sesión)
    print("\n🟣 ESCENARIO 5: MEJORA - Consulta sobre involucrados usando memoria de sesión")
    
    docs5 = await retriever3._aget_relevant_documents("y los involucrados en ese caso?")
    print(f"📄 Documentos encontrados: {len(docs5)}")
    if docs5:
        print(f"🔍 Primer documento: {docs5[0].page_content[:150]}...")
        print(f"📋 Expediente: {docs5[0].metadata.get('expediente_numero', 'No especificado')}")
        print("✅ MEJORA FUNCIONANDO - Encuentra información usando memoria de sesión")
    else:
        print("❌ MEJORA NO FUNCIONÓ")
    
    print("\n" + "=" * 80)
    print("🎯 RESUMEN DE LA PRUEBA COMPLETADA")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_context_memory())