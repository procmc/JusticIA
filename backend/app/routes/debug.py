from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.usuario import T_Usuario
from app.db.models.rol import T_Rol
from app.repositories.usuario_repository import UsuarioRepository
from app.vectorstore.vectorstore import get_vectorstore, search_similar_documents
from app.embeddings.embeddings import get_embedding
from app.config.config import COLLECTION_NAME
from typing import Optional

router = APIRouter(tags=["debug"])

@router.get("/usuario-por-email/{email}")
async def debug_usuario_por_email(email: str, db: Session = Depends(get_db)):
    """Debug: Ver datos completos de un usuario por email incluyendo rol"""
    usuario = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
    
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    # Obtener información del rol
    rol_info = None
    if usuario.CN_Id_rol:
        rol = db.query(T_Rol).filter(T_Rol.CN_Id_rol == usuario.CN_Id_rol).first()
        if rol:
            rol_info = {
                "id": rol.CN_Id_rol,
                "nombre": rol.CT_Nombre_rol
            }
    
    return {
        "usuario": {
            "id": usuario.CN_Id_usuario,
            "email": usuario.CT_Correo,
            "nombre_usuario": usuario.CT_Nombre_usuario,
            "nombre": usuario.CT_Nombre,
            "apellido_uno": usuario.CT_Apellido_uno,
            "apellido_dos": usuario.CT_Apellido_dos,
            "nombre_completo": f"{usuario.CT_Nombre} {usuario.CT_Apellido_uno}" + (f" {usuario.CT_Apellido_dos}" if usuario.CT_Apellido_dos else ""),
            "rol_id": usuario.CN_Id_rol,
            "estado_id": usuario.CN_Id_estado
        },
        "rol": rol_info
    }

@router.get("/usuarios")
async def listar_usuarios_debug(db: Session = Depends(get_db)):
    """Endpoint temporal para debug - ver todos los usuarios"""
    usuarios = db.query(T_Usuario).all()
    resultado = []
    
    for usuario in usuarios:
        resultado.append({
            "id": usuario.CN_Id_usuario,
            "email": usuario.CT_Correo,
            "nombre_usuario": usuario.CT_Nombre_usuario,
            "nombre": f"{usuario.CT_Nombre} {usuario.CT_Apellido_uno}",
            "hash_password_preview": usuario.CT_Contrasenna[:50] + "...",
            "rol_id": usuario.CN_Id_rol,
            "estado_id": usuario.CN_Id_estado
        })
    
    return resultado

@router.post("/test-password")
async def test_password_debug(
    email: str, 
    password: str, 
    db: Session = Depends(get_db)
):
    """Endpoint temporal para debug - probar contraseña paso a paso"""
    repo = UsuarioRepository()
    
    # Paso 1: Buscar usuario por CT_Nombre_usuario
    usuario_por_nombre = db.query(T_Usuario).filter(T_Usuario.CT_Nombre_usuario == email).first()
    
    # Paso 2: Buscar usuario por CT_Correo
    usuario_por_correo = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
    
    resultado = {
        "email_buscado": email,
        "password_probado": password,
        "usuario_encontrado_por_nombre_usuario": usuario_por_nombre is not None,
        "usuario_encontrado_por_correo": usuario_por_correo is not None,
    }
    
    if usuario_por_nombre:
        resultado["datos_usuario_nombre"] = {
            "id": usuario_por_nombre.CN_Id_usuario,
            "email": usuario_por_nombre.CT_Correo,
            "nombre_usuario": usuario_por_nombre.CT_Nombre_usuario,
        }
        # Probar contraseña
        password_valida = repo.pwd_context.verify(password, usuario_por_nombre.CT_Contrasenna)
        resultado["password_valida_nombre_usuario"] = password_valida
    
    if usuario_por_correo:
        resultado["datos_usuario_correo"] = {
            "id": usuario_por_correo.CN_Id_usuario,
            "email": usuario_por_correo.CT_Correo,
            "nombre_usuario": usuario_por_correo.CT_Nombre_usuario,
        }
        # Probar contraseña
        password_valida = repo.pwd_context.verify(password, usuario_por_correo.CT_Contrasenna)
        resultado["password_valida_correo"] = password_valida
    
    return resultado

@router.post("/reset-password")
async def reset_password_debug(
    email: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """Endpoint temporal para debug - resetear contraseña de un usuario"""
    repo = UsuarioRepository()
    
    # Buscar usuario por correo
    usuario = db.query(T_Usuario).filter(T_Usuario.CT_Correo == email).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Hashear nueva contraseña
    nueva_contrasenna_hash = repo._hash_password(new_password)
    
    # Actualizar contraseña
    usuario.CT_Contrasenna = nueva_contrasenna_hash
    db.commit()
    
    return {
        "message": "Contraseña actualizada exitosamente",
        "email": email,
        "nueva_password": new_password,
        "usuario_id": usuario.CN_Id_usuario
    }

# ===== ENDPOINTS DEBUG MILVUS =====

@router.get("/milvus/stats")
async def milvus_stats():
    """Obtener estadísticas de la colección Milvus"""
    try:
        client = await get_vectorstore()
        
        # Estadísticas básicas
        stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
        
        # Lista de colecciones
        collections = client.list_collections()
        
        return {
            "collection_name": COLLECTION_NAME,
            "collections_available": collections,
            "stats": stats,
            "status": "✅ Milvus conectado"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "❌ Error conectando a Milvus"
        }

@router.get("/milvus/sample/{limit}")
async def milvus_sample_documents(limit: int = 5):
    """Obtener documentos de muestra de Milvus"""
    try:
        client = await get_vectorstore()
        
        # Intentar primero con una consulta específica por id
        try:
            results = client.query(
                collection_name=COLLECTION_NAME,
                expr="id_documento >= 0",  # Expresión que incluya todos los documentos
                limit=limit,
                output_fields=["id_chunk", "id_expediente", "id_documento", "texto", "tipo_archivo", "fecha_carga", "nombre_archivo", "numero_expediente"]
            )
            
            if not results:
                # Si no hay resultados, intentar con otra expresión
                results = client.query(
                    collection_name=COLLECTION_NAME,
                    expr="",  # Sin filtros
                    limit=limit,
                    output_fields=["*"]  # Todos los campos
                )
        except Exception as query_error:
            # Si query falla, usar search con un vector dummy
            dummy_vector = [0.0] * 768  # Vector de ceros del tamaño correcto (768 dimensiones)
            
            # Parámetros de búsqueda para HNSW con métrica COSINE
            search_params = {
                "metric_type": "COSINE",
                "params": {"ef": 64}
            }
            
            results = client.search(
                collection_name=COLLECTION_NAME,
                data=[dummy_vector],
                anns_field="embedding",
                search_params=search_params,
                limit=limit,
                output_fields=["id_chunk", "id_expediente", "id_documento", "texto", "tipo_archivo", "fecha_carga", "nombre_archivo", "numero_expediente"]
            )
            
            # Convertir resultados de search a formato más legible
            if results and len(results) > 0:
                # Los resultados de search tienen una estructura diferente
                formatted_results = []
                for hit in results[0]:
                    formatted_results.append({
                        "id_chunk": hit.get("id_chunk", ""),
                        "score": getattr(hit, 'score', 0.0),
                        "entity": hit
                    })
                results = formatted_results
        
        return {
            "total_encontrados": len(results) if results else 0,
            "documentos": results[:limit] if results else [],
            "status": "✅ Consulta exitosa",
            "collection_name": COLLECTION_NAME
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "❌ Error consultando documentos",
            "collection_name": COLLECTION_NAME
        }

@router.post("/milvus/search-test")
async def milvus_search_test(query: str, top_k: int = 5):
    """Probar búsqueda vectorial en Milvus"""
    try:
        # 1. Generar embedding
        print(f"Generando embedding para: {query}")
        embedding = await get_embedding(query)
        print(f"Embedding generado: {len(embedding)} dimensiones")
        
        # 2. Buscar documentos similares
        print(f"Buscando en Milvus con top_k={top_k}")
        results = await search_similar_documents(
            query_embedding=embedding,
            limit=top_k,
            filters=None
        )
        
        # 3. Procesar resultados
        processed_results = []
        for i, doc in enumerate(results):
            entity = doc.get("entity", {})
            distance = doc.get("distance", 1.0)
            similarity = round(1 - distance, 3)
            
            processed_results.append({
                "rank": i + 1,
                "id_chunk": entity.get("id_chunk", ""),
                "id_expediente": entity.get("id_expediente", ""),
                "numero_expediente": entity.get("numero_expediente", ""),
                "id_documento": entity.get("id_documento", ""),
                "nombre_archivo": entity.get("nombre_archivo", ""),
                "tipo_archivo": entity.get("tipo_archivo", ""),
                "similarity": similarity,
                "distance": distance,
                "texto_preview": entity.get("texto", "")[:200] + "..." if entity.get("texto") else ""
            })
        
        return {
            "query": query,
            "embedding_dimensions": len(embedding),
            "documentos_encontrados": len(results),
            "resultados": processed_results,
            "status": "✅ Búsqueda exitosa"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "status": "❌ Error en búsqueda"
        }

@router.get("/milvus/connection-test")
async def milvus_connection_test():
    """Prueba simple de conexión y configuración de Milvus"""
    try:
        client = await get_vectorstore()
        
        # Test básico de conectividad
        collections = client.list_collections()
        
        # Verificar que la colección existe
        collection_exists = COLLECTION_NAME in collections
        
        # Intentar obtener estadísticas básicas
        stats = None
        if collection_exists:
            try:
                stats = client.get_collection_stats(collection_name=COLLECTION_NAME)
            except Exception as stats_error:
                stats = f"Error obteniendo stats: {str(stats_error)}"
        
        return {
            "status": "✅ Conexión exitosa",
            "milvus_uri": "***" if "***" in str(client) else "configurado", 
            "collections_available": collections,
            "target_collection": COLLECTION_NAME,
            "collection_exists": collection_exists,
            "collection_stats": stats
        }
    except Exception as e:
        import traceback
        return {
            "status": "❌ Error de conexión",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/milvus/simple-search-test")
async def milvus_simple_search_test(query_text: str = "justicia"):
    """Prueba simple de búsqueda para verificar que los parámetros funcionan"""
    try:
        # 1. Generar embedding simple
        embedding = await get_embedding(query_text)
        
        # 2. Hacer búsqueda directa usando el cliente
        client = await get_vectorstore()
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64}
        }
        
        results = client.search(
            collection_name=COLLECTION_NAME,
            data=[embedding],
            anns_field="embedding",
            search_params=search_params,
            limit=3,
            output_fields=["id_chunk", "texto", "nombre_archivo"]
        )
        
        # Procesar resultados
        processed = []
        if results and len(results) > 0:
            for hit in results[0]:
                processed.append({
                    "id_chunk": hit.get("id_chunk", ""),
                    "distance": getattr(hit, 'distance', 0.0),
                    "similarity": round(1 - getattr(hit, 'distance', 1.0), 3),
                    "texto_preview": hit.get("texto", "")[:100] + "...",
                    "archivo": hit.get("nombre_archivo", "")
                })
        
        return {
            "status": "✅ Búsqueda exitosa",
            "query": query_text,
            "total_results": len(processed),
            "results": processed
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "❌ Error en búsqueda", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }
