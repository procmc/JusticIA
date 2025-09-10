from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import time
from collections import defaultdict
from sqlalchemy.orm import Session

from app.schemas.similarity_schemas import (
    SimilaritySearchRequest, 
    SimilaritySearchResponse, 
    SimilarCase, 
    DocumentMatch
)
from app.embeddings.embeddings import get_embedding
from app.vectorstore.vectorstore import search_similar_documents
from app.repositories.expediente_repository import ExpedienteRepository
from app.db.database import get_db
from app.config.config import COLLECTION_NAME


class SimilarityService:
    """Servicio especializado para búsqueda de casos similares"""
    
    def __init__(self):
        self.expediente_repo = ExpedienteRepository()

    async def search_similar_cases(
        self, 
        request: SimilaritySearchRequest,
        user_id: Optional[str] = None
    ) -> SimilaritySearchResponse:
        """
        Función principal para búsqueda de casos similares
        
        Args:
            request: Parámetros de búsqueda
            user_id: ID del usuario que realiza la búsqueda (para auditoría)
            
        Returns:
            SimilaritySearchResponse: Resultados de la búsqueda
        """
        start_time = time.time()
        
        try:
            # 1. Validar y obtener criterio de búsqueda
            search_criteria = self._extract_search_criteria(request)
            
            # 2. Realizar búsqueda según el modo
            if request.search_mode == "description":
                if not request.query_text:
                    raise ValueError("query_text es requerido para búsqueda por descripción")
                raw_results = await self._search_by_description(
                    request.query_text, 
                    request.limit, 
                    request.similarity_threshold
                )
            elif request.search_mode == "expedient":
                if not request.expedient_number:
                    raise ValueError("expedient_number es requerido para búsqueda por expediente")
                raw_results = await self._search_by_expedient(
                    request.expedient_number, 
                    request.limit, 
                    request.similarity_threshold
                )
            else:
                raise ValueError(f"Modo de búsqueda no válido: {request.search_mode}")
            
            # 3. Procesar y agrupar resultados por expediente
            similar_cases = await self._process_and_group_results(
                raw_results, 
                request.similarity_threshold
            )
            
            # 4. Calcular métricas
            execution_time = (time.time() - start_time) * 1000
            total_documents_analyzed = len(raw_results)
            
            # 5. Crear respuesta
            response = SimilaritySearchResponse(
                search_criteria=search_criteria,
                search_mode=request.search_mode,
                total_results=len(similar_cases),
                execution_time_ms=round(execution_time, 2),
                similarity_threshold=request.similarity_threshold,
                similar_cases=similar_cases,
                total_documents_analyzed=total_documents_analyzed
            )
            
            # TODO: Registrar en bitácora si user_id está disponible
            # await self._log_search_activity(user_id, request, response)
            
            return response
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            print(f"Error en búsqueda de similares: {str(e)}")
            
            # Retornar respuesta vacía pero válida en caso de error
            return SimilaritySearchResponse(
                search_criteria=search_criteria if 'search_criteria' in locals() else "Error",
                search_mode=request.search_mode,
                total_results=0,
                execution_time_ms=round(execution_time, 2),
                similarity_threshold=request.similarity_threshold,
                similar_cases=[],
                total_documents_analyzed=0
            )

    async def _search_by_description(
        self, 
        query_text: str, 
        limit: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Búsqueda por descripción de texto libre con mejoras de ranking"""
        
        print(f"🔍 Buscando por descripción: '{query_text[:100]}...'")
        
        # 1. Generar embedding del texto de consulta
        query_embedding = await get_embedding(query_text)
        print(f"✅ Embedding generado: {len(query_embedding)} dimensiones")
        
        # 2. Buscar documentos similares en vectorstore
        similar_docs = await search_similar_documents(
            query_embedding=query_embedding,
            limit=limit * 5,  # Buscar más docs para mejor ranking
            filters=None  # Sin filtros para búsqueda general
        )
        
        print(f"📄 Documentos encontrados en vectorstore: {len(similar_docs)}")
        
        # 3. Mejorar ranking con boost de relevancia temática
        enhanced_docs = self._enhance_ranking_with_context(similar_docs, query_text)
        
        return enhanced_docs

    async def _search_by_expedient(
        self, 
        expedient_number: str, 
        limit: int, 
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Búsqueda por número de expediente específico"""
        
        print(f"🔍 Buscando expedientes similares a: {expedient_number}")
        
        # 1. Verificar que el expediente existe
        db = next(get_db())
        try:
            expediente_base = self.expediente_repo.obtener_por_numero(db, expedient_number)
            if not expediente_base:
                print(f"⚠️ Expediente {expedient_number} no encontrado")
                return []
            
            print(f"✅ Expediente base encontrado: ID {expediente_base.CN_Id_expediente}")
            
        finally:
            db.close()
        
        # 2. Obtener documentos del expediente base para crear embedding promedio
        expedient_docs = await self._get_expedient_documents(expedient_number)
        
        if not expedient_docs:
            print(f"⚠️ No se encontraron documentos para el expediente {expedient_number}")
            return []
        
        # 3. Crear embedding representativo del expediente
        expedient_embedding = await self._create_expedient_embedding(expedient_docs)
        
        # 4. Buscar expedientes similares (excluyendo el mismo expediente)
        similar_docs = await search_similar_documents(
            query_embedding=expedient_embedding,
            limit=limit * 3,
            filters=f'numero_expediente != "{expedient_number}"'  # Excluir el expediente base
        )
        
        print(f"📄 Expedientes similares encontrados: {len(similar_docs)}")
        
        return similar_docs

    async def _get_expedient_documents(self, expedient_number: str) -> List[Dict[str, Any]]:
        """Obtiene todos los documentos de un expediente específico"""
        
        # Buscar con filtro de expediente específico
        dummy_embedding = [0.1] * 768  # Vector dummy para búsqueda con filtro
        
        docs = await search_similar_documents(
            query_embedding=dummy_embedding,
            limit=1000,  # Obtener todos los documentos del expediente
            filters=f'numero_expediente == "{expedient_number}"'
        )
        
        return docs

    async def _create_expedient_embedding(self, docs: List[Dict[str, Any]]) -> List[float]:
        """Crea un embedding representativo de un expediente completo"""
        
        # Estrategia: concatenar los textos más relevantes y generar un embedding
        texts = []
        for doc in docs[:10]:  # Tomar hasta 10 documentos más relevantes
            entity = doc.get("entity", {})
            texto = entity.get("texto", "")
            if texto.strip():
                texts.append(texto[:500])  # Tomar hasta 500 chars por documento
        
        if not texts:
            # Fallback: usar el número de expediente
            combined_text = f"Expediente judicial número {docs[0]['entity'].get('numero_expediente', '')}"
        else:
            combined_text = " ".join(texts)
        
        # Generar embedding del texto combinado
        return await get_embedding(combined_text)

    async def _process_and_group_results(
        self, 
        raw_results: List[Dict[str, Any]], 
        threshold: float
    ) -> List[SimilarCase]:
        """Procesa y agrupa resultados por expediente con ranking mejorado"""
        
        print(f"🔄 Procesando {len(raw_results)} documentos...")
        
        # Agrupar documentos por expediente manteniendo información de boost
        expedients_dict = defaultdict(list)
        
        for doc in raw_results:
            entity = doc.get("entity", {})
            distance = doc.get("distance", 1.0)
            original_distance = doc.get("original_distance", distance)
            boost_factor = doc.get("boost_factor", 1.0)
            matched_legal_area = doc.get("matched_legal_area")
            
            # Convertir distancia a similitud y filtrar por umbral
            similarity = 1.0 - distance
            if similarity < threshold:
                continue
                
            expedient_number = entity.get("numero_expediente", "")
            if not expedient_number:
                continue
                
            expedients_dict[expedient_number].append({
                "document": entity,
                "similarity": similarity,
                "distance": distance,
                "original_similarity": 1.0 - original_distance,
                "boost_factor": boost_factor,
                "matched_legal_area": matched_legal_area
            })
        
        print(f"📊 Expedientes únicos encontrados: {len(expedients_dict)}")
        
        # Convertir a objetos SimilarCase
        similar_cases = []
        db = next(get_db())
        
        try:
            for expedient_number, docs in expedients_dict.items():
                # Obtener información del expediente desde la BD
                expediente = self.expediente_repo.obtener_por_numero(db, expedient_number)
                if not expediente:
                    continue
                
                # Calcular similitud mejorada del expediente
                # Usar el máximo de similitud mejorada (no promedio) para priorizar el mejor match
                max_similarity = max(d["similarity"] for d in docs)
                avg_boost = sum(d["boost_factor"] for d in docs) / len(docs)
                
                # Determinar área legal predominante
                legal_areas = [d["matched_legal_area"] for d in docs if d["matched_legal_area"]]
                predominant_area = max(set(legal_areas), key=legal_areas.count) if legal_areas else None
                
                # Crear objetos DocumentMatch ordenados por similitud
                docs_sorted = sorted(docs, key=lambda x: x["similarity"], reverse=True)
                matched_documents = []
                
                for doc_data in docs_sorted[:5]:  # Top 5 documentos por expediente
                    doc_entity = doc_data["document"]
                    matched_documents.append(DocumentMatch(
                        document_id=doc_entity.get("id_documento", 0),
                        document_name=doc_entity.get("nombre_archivo", "Documento sin nombre"),
                        similarity_score=doc_data["similarity"],
                        text_fragment=self._truncate_text(doc_entity.get("texto", ""), 200),
                        page_number=doc_entity.get("pagina_inicio")
                    ))
                
                # Crear objeto SimilarCase
                similar_case = SimilarCase(
                    expedient_id=expediente.CN_Id_expediente,
                    expedient_number=expedient_number,
                    similarity_percentage=round(max_similarity * 100, 1),
                    document_count=len(docs),
                    matched_documents=matched_documents,
                    creation_date=expediente.CF_Fecha_creacion,
                    matter_type=self._extract_matter_type(expedient_number)
                )
                
                # Agregar metadatos de ranking para debugging
                similar_case.court_instance = f"Boost: {avg_boost:.2f}x" if avg_boost > 1.0 else None
                
                similar_cases.append(similar_case)
        
        finally:
            db.close()
        
        # Ordenar por similitud mejorada (ya considera el boost)
        similar_cases.sort(key=lambda x: x.similarity_percentage, reverse=True)
        
        print(f"✅ Casos similares procesados: {len(similar_cases)}")
        
        return similar_cases

    def _extract_search_criteria(self, request: SimilaritySearchRequest) -> str:
        """Extrae el criterio de búsqueda legible"""
        if request.search_mode == "description" and request.query_text:
            return request.query_text.strip()
        elif request.search_mode == "expedient" and request.expedient_number:
            return f"Expediente: {request.expedient_number}"
        return "Criterio no especificado"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca texto manteniendo palabras completas"""
        if len(text) <= max_length:
            return text
        
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Si el último espacio está cerca del final
            truncated = truncated[:last_space]
        
        return truncated + "..."

    def _extract_matter_type(self, expedient_number: str) -> Optional[str]:
        """Extrae el tipo de materia del número de expediente"""
        try:
            # Patrón típico: YYYY-NNN-NN-XX donde XX es el tipo de materia
            parts = expedient_number.split('-')
            if len(parts) >= 4:
                matter_code = parts[3].upper()
                matter_types = {
                    'CI': 'Civil',
                    'PE': 'Penal',
                    'LA': 'Laboral',
                    'AD': 'Administrativo',
                    'FA': 'Familia',
                    'CO': 'Comercial',
                    'TU': 'Tutela',
                    'AM': 'Amparo'
                }
                return matter_types.get(matter_code, matter_code)
        except:
            pass
        
        return None


    def _enhance_ranking_with_context(
        self, 
        docs: List[Dict[str, Any]], 
        query_text: str
    ) -> List[Dict[str, Any]]:
        """
        Mejora el ranking de documentos considerando contexto temático y términos clave
        """
        print(f"🎯 Mejorando ranking para query: '{query_text}'")
        
        # Términos clave por área legal que dan boost de relevancia
        legal_keywords = {
            'penal': {
                'keywords': [
                    'narcotrafico', 'narcotráfico', 'estupefacientes', 'drogas', 'tráfico ilícito',
                    'delito', 'crimen', 'penal', 'criminal', 'homicidio', 'robo', 'hurto',
                    'violación', 'secuestro', 'extorsión', 'lavado de dinero', 'sicariato'
                ],
                'boost_factor': 1.3
            },
            'civil': {
                'keywords': [
                    'daños', 'perjuicios', 'contractual', 'responsabilidad civil', 'indemnización',
                    'propiedad', 'servidumbre', 'usucapión', 'reivindicación'
                ],
                'boost_factor': 1.2
            },
            'laboral': {
                'keywords': [
                    'despido', 'salario', 'prestaciones', 'trabajo', 'empleado', 'patrón',
                    'cesantía', 'preaviso', 'aguinaldo', 'vacaciones'
                ],
                'boost_factor': 1.15
            },
            'familia': {
                'keywords': [
                    'alimentos', 'guarda', 'custodia', 'divorcio', 'pensión alimentaria',
                    'patria potestad', 'régimen de visitas', 'adopción'
                ],
                'boost_factor': 1.1
            }
        }
        
        query_lower = query_text.lower()
        
        enhanced_docs = []
        for doc in docs:
            entity = doc.get("entity", {})
            texto = entity.get("texto", "").lower()
            expedient_number = entity.get("numero_expediente", "")
            original_distance = doc.get("distance", 1.0)
            
            # Calcular boost basado en coincidencias temáticas
            boost_factor = 1.0
            matched_area = None
            
            for area, config in legal_keywords.items():
                # Verificar si la query contiene términos del área
                query_matches = any(keyword in query_lower for keyword in config['keywords'])
                # Verificar si el documento contiene términos del área
                doc_matches = any(keyword in texto for keyword in config['keywords'])
                
                if query_matches and doc_matches:
                    boost_factor = max(boost_factor, config['boost_factor'])
                    matched_area = area
                    print(f"📈 Boost aplicado: {area} ({config['boost_factor']}x) para expediente {expedient_number}")
                    break
            
            # Boost adicional por coincidencia exacta de términos
            exact_match_boost = 1.0
            query_words = set(query_lower.split())
            doc_words = set(texto.split())
            
            # Calcular intersección de palabras
            common_words = query_words.intersection(doc_words)
            if len(common_words) > 0:
                exact_match_boost = 1.0 + (len(common_words) * 0.1)  # 10% boost por palabra común
                print(f"🎯 Boost por palabras exactas: {exact_match_boost:.2f}x ({len(common_words)} palabras)")
            
            # Aplicar boost total
            total_boost = boost_factor * exact_match_boost
            enhanced_distance = original_distance / total_boost
            
            # Crear documento mejorado
            enhanced_doc = doc.copy()
            enhanced_doc["distance"] = enhanced_distance
            enhanced_doc["original_distance"] = original_distance
            enhanced_doc["boost_factor"] = total_boost
            enhanced_doc["matched_legal_area"] = matched_area
            
            enhanced_docs.append(enhanced_doc)
        
        # Reordenar por nueva distancia (menor = más similar)
        enhanced_docs.sort(key=lambda x: x["distance"])
        
        print(f"✅ Ranking mejorado: {len(enhanced_docs)} documentos reordenados")
        
        return enhanced_docs


# Instancia singleton del servicio
similarity_service = SimilarityService()
