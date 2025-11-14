"""Repositorio de Acceso a Datos de Documentos Judiciales.

Este módulo implementa el patrón Repository para abstraer el acceso a datos
de documentos judiciales (archivos PDF, DOCX, imágenes, audios) asociados a expedientes.
Proporciona operaciones CRUD y consultas especializadas sobre la tabla T_Documento.

Arquitectura de documentos:
    Cada documento pertenece a un expediente y tiene un estado de procesamiento:
        1. PENDIENTE: Recién subido, en cola
        2. EN_PROCESO: Siendo procesado por Celery (Tika/Whisper)
        3. COMPLETADO: Procesado exitosamente, embeddings en Milvus
        4. ERROR: Falló el procesamiento

Operaciones principales:
    - crear: Crear documento asociado a expediente
    - actualizar_estado: Cambiar estado de procesamiento
    - listar_por_expediente: Obtener documentos de un expediente
    - obtener_ids_procesados: IDs de documentos listos para búsqueda
    - verificar_esta_procesado: Validar si archivo puede descargarse

Modelo de datos:
    T_Documento:
        - CN_Id_documento (int, PK): ID autoincremental
        - CN_Id_expediente (int, FK): Expediente al que pertenece
        - CT_Nombre_archivo (str): Nombre del archivo
        - CT_Tipo_archivo (str): Extensión (.pdf, .docx, .mp3, etc.)
        - CT_Ruta_archivo (str): Ruta relativa desde backend/uploads/
        - CF_Fecha_carga (datetime): Fecha de carga del archivo
        - CN_Id_estado (int, FK): Estado de procesamiento actual

Flujo de procesamiento:
    1. crear() → Estado PENDIENTE
    2. Celery task inicia → actualizar_estado(EN_PROCESO)
    3. Procesamiento exitoso → actualizar_estado(COMPLETADO)
    4. Solo documentos COMPLETADOS aparecen en búsquedas RAG y descargas

Example:
    ```python
    from app.repositories.documento_repository import DocumentoRepository
    from app.db.database import get_db
    
    repo = DocumentoRepository()
    db = next(get_db())
    
    # Crear documento
    documento = repo.crear(
        db=db,
        expediente=expediente_obj,
        nombre_archivo='demanda.pdf',
        tipo_archivo='pdf',
        estado_procesamiento=estado_pendiente,
        ruta_archivo='uploads/00-000123-0456-PE/demanda.pdf'
    )
    
    # Actualizar estado después de procesamiento
    repo.actualizar_estado(db, documento, estado_completado)
    
    # Obtener solo documentos procesados para búsqueda
    docs_procesados = repo.listar_por_expediente(db, expediente, solo_procesados=True)
    
    # Verificar si archivo puede descargarse
    puede_descargar = repo.verificar_esta_procesado(db, '00-000123-0456-PE', 'demanda.pdf')
    ```

Note:
    Los métodos obtener_ids_procesados y verificar_esta_procesado son críticos
    para filtrar documentos en búsquedas vectoriales y validar descargas.

See Also:
    - app.db.models.documento.T_Documento: Modelo SQLAlchemy
    - app.db.models.estado_procesamiento.T_Estado_procesamiento: Estados disponibles
    - app.services.expediente_service.ExpedienteService: Lógica de negocio
    - tasks.procesar_ingesta: Tarea Celery que procesa documentos
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.documento import T_Documento
from app.db.models.expediente import T_Expediente
from app.db.models.estado_procesamiento import T_Estado_procesamiento
from datetime import datetime


class DocumentoRepository:
    """Repositorio de acceso a datos para documentos judiciales.
    
    Gestiona documentos asociados a expedientes, incluyendo su estado de
    procesamiento y metadatos. Fundamental para el pipeline de ingesta y RAG.
    
    Attributes:
        Ninguno. Todas las operaciones son stateless y reciben la sesión db como parámetro.
    """
    
    def obtener_por_id(self, db: Session, documento_id: int) -> Optional[T_Documento]:
        """
        Obtiene un documento por su ID.
        
        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            Optional[T_Documento]: Documento encontrado o None
        """
        stmt = select(T_Documento).where(T_Documento.CN_Id_documento == documento_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
    
    def crear(
        self,
        db: Session,
        expediente: T_Expediente,
        nombre_archivo: str,
        tipo_archivo: str,
        estado_procesamiento: T_Estado_procesamiento,
        ruta_archivo: Optional[str] = None,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Crea un nuevo documento.
        
        Args:
            db: Sesión de base de datos
            expediente: Expediente al que pertenece
            nombre_archivo: Nombre del archivo
            tipo_archivo: Tipo/extensión del archivo
            estado_procesamiento: Estado inicial del documento
            ruta_archivo: Ruta del archivo (opcional)
            auto_commit: Si hacer commit automáticamente
            
        Returns:
            T_Documento: Documento creado
            
        Raises:
            Exception: Si hay error en la creación
        """
        try:
            documento = T_Documento(
                CT_Nombre_archivo=nombre_archivo,
                CT_Tipo_archivo=tipo_archivo,
                CT_Ruta_archivo=ruta_archivo or "",
                CF_Fecha_carga=datetime.utcnow(),
                CN_Id_estado=estado_procesamiento.CN_Id_estado
            )
            
            # Asociar con el expediente
            expediente.documentos.append(documento)
            
            db.add(documento)
            
            if auto_commit:
                db.commit()
                db.refresh(documento)
            else:
                db.flush()
            
            return documento
            
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error creando documento: {str(e)}")
    
    def actualizar_estado(
        self,
        db: Session,
        documento: T_Documento,
        nuevo_estado: T_Estado_procesamiento,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Actualiza el estado de un documento.
        
        Args:
            db: Sesión de base de datos
            documento: Documento a actualizar
            nuevo_estado: Nuevo estado de procesamiento
            auto_commit: Si hacer commit automáticamente
            
        Returns:
            T_Documento: Documento actualizado
            
        Raises:
            Exception: Si hay error en la actualización
        """
        try:
            documento.CN_Id_estado = nuevo_estado.CN_Id_estado
            
            db.add(documento)
            
            if auto_commit:
                db.commit()
                db.refresh(documento)
            
            return documento
            
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error actualizando estado del documento: {str(e)}")
    
    def actualizar_ruta_archivo(
        self,
        db: Session,
        documento: T_Documento,
        ruta_archivo: str,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Actualiza la ruta de archivo de un documento.
        
        Args:
            db: Sesión de base de datos
            documento: Documento a actualizar
            ruta_archivo: Nueva ruta del archivo
            auto_commit: Si hacer commit automáticamente
            
        Returns:
            T_Documento: Documento actualizado
        """
        try:
            documento.CT_Ruta_archivo = ruta_archivo
            
            db.add(documento)
            
            if auto_commit:
                db.commit()
                db.refresh(documento)
            
            return documento
            
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error actualizando ruta del archivo: {str(e)}")
    
    def listar_por_expediente(self, db: Session, expediente: T_Expediente, solo_procesados: bool = False) -> List[T_Documento]:
        """
        Lista todos los documentos de un expediente.
        
        Args:
            db: Sesión de base de datos
            expediente: Expediente del cual listar documentos
            solo_procesados: Si True, retorna solo documentos con estado "Procesado"
            
        Returns:
            List[T_Documento]: Lista de documentos del expediente
        """
        documentos = expediente.documentos
        
        if solo_procesados:
            # Filtrar solo documentos procesados
            documentos = [
                doc for doc in documentos 
                if doc.estado and doc.estado.CT_Nombre_estado == "Procesado"
            ]
        
        return documentos
    
    def obtener_ids_procesados(self, db: Session) -> set:
        """
        Obtiene los IDs de todos los documentos con estado 'Procesado'.
        Método centralizado para filtrado en búsquedas.
        
        Args:
            db: Sesión de base de datos
            
        Returns:
            set: Set de IDs de documentos procesados
        """
        try:
            stmt = select(T_Documento.CN_Id_documento).join(
                T_Estado_procesamiento,
                T_Documento.CN_Id_estado == T_Estado_procesamiento.CN_Id_estado
            ).where(
                T_Estado_procesamiento.CT_Nombre_estado == "Procesado"
            )
            
            result = db.execute(stmt)
            return {doc_id for (doc_id,) in result.fetchall()}
            
        except Exception as e:
            print(f"Error obteniendo IDs de documentos procesados: {e}")
            return set()
    
    def listar_por_expediente_y_nombres(
        self, 
        db: Session, 
        expediente_numero: str, 
        solo_procesados: bool = True
    ) -> List[str]:
        """
        Lista nombres de archivos de un expediente.
        Útil para filtrado en file_management_service.
        
        Args:
            db: Sesión de base de datos
            expediente_numero: Número del expediente
            solo_procesados: Si True, retorna solo archivos procesados
            
        Returns:
            List[str]: Lista de nombres de archivos
        """
        try:
            query = db.query(T_Documento.CT_Nombre_archivo).join(
                T_Expediente,
                T_Documento.CN_Id_expediente == T_Expediente.CN_Id_expediente
            ).filter(
                T_Expediente.CT_Num_expediente == expediente_numero
            )
            
            if solo_procesados:
                query = query.join(
                    T_Estado_procesamiento,
                    T_Documento.CN_Id_estado == T_Estado_procesamiento.CN_Id_estado
                ).filter(
                    T_Estado_procesamiento.CT_Nombre_estado == "Procesado"
                )
            
            return [nombre for (nombre,) in query.all()]
            
        except Exception as e:
            print(f"Error listando archivos por expediente: {e}")
            return []
    
    def verificar_esta_procesado(
        self, 
        db: Session, 
        expediente_numero: str, 
        nombre_archivo: str
    ) -> bool:
        """
        Verifica si un archivo específico está procesado.
        Útil para validación en descarga de archivos.
        
        Args:
            db: Sesión de base de datos
            expediente_numero: Número del expediente
            nombre_archivo: Nombre del archivo
            
        Returns:
            bool: True si el archivo está procesado, False en caso contrario
        """
        try:
            stmt = select(T_Estado_procesamiento.CT_Nombre_estado).select_from(
                T_Documento
            ).join(
                T_Expediente,
                T_Documento.CN_Id_expediente == T_Expediente.CN_Id_expediente
            ).join(
                T_Estado_procesamiento,
                T_Documento.CN_Id_estado == T_Estado_procesamiento.CN_Id_estado
            ).where(
                T_Expediente.CT_Num_expediente == expediente_numero,
                T_Documento.CT_Nombre_archivo == nombre_archivo
            )
            
            result = db.execute(stmt)
            estado = result.scalar_one_or_none()
            
            return estado == "Procesado" if estado else False
            
        except Exception as e:
            print(f"Error verificando estado de archivo: {e}")
            return False
