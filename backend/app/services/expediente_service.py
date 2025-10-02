from sqlalchemy.orm import Session
from app.db.models.expediente import T_Expediente
from app.db.models.documento import T_Documento
from app.db.models.estado_procesamiento import T_Estado_procesamiento
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.estado_procesamiento_repository import EstadoProcesamientoRepository
from app.config.file_config import ALLOWED_EXTENSIONS
from datetime import datetime
from typing import Optional, List
import os
from pathlib import Path
from fastapi import UploadFile

class ExpedienteService:
    """Servicio para manejar lógica de negocio de expedientes y documentos"""
    
    def __init__(self):
        self.expediente_repo = ExpedienteRepository()
        self.documento_repo = DocumentoRepository()
        self.estado_repo = EstadoProcesamientoRepository()
    
    async def obtener_estado_procesamiento(self, db: Session, nombre_estado: str) -> T_Estado_procesamiento:
        """
        Obtiene un estado de procesamiento por su nombre.
        Valida que el estado exista en el sistema.
        
        Args:
            db: Sesión de base de datos
            nombre_estado: Nombre del estado ('Pendiente', 'Procesado', 'Error')
            
        Returns:
            T_Estado_procesamiento: Estado encontrado
            
        Raises:
            Exception: Si no se encuentra el estado
        """
        estado = self.estado_repo.obtener_por_nombre(db, nombre_estado)
        
        if not estado:
            raise Exception(f"Estado de procesamiento '{nombre_estado}' no encontrado")
        
        return estado
    
    async def buscar_o_crear_expediente(self, db: Session, numero_expediente: str) -> T_Expediente:
        """
        Lógica de negocio para buscar o crear expediente.
        Valida formato del número de expediente y maneja la creación.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            T_Expediente: Expediente encontrado o creado
            
        Raises:
            Exception: Si hay error en validaciones o creación
        """
        # Validaciones de negocio
        if not numero_expediente or not numero_expediente.strip():
            raise Exception("El número de expediente no puede estar vacío")
        
        numero_expediente = numero_expediente.strip()
        
        # Buscar o crear usando el repository
        try:
            expediente = self.expediente_repo.buscar_o_crear(db, numero_expediente)
            print(f"Expediente obtenido/creado: {expediente.CT_Num_expediente}")
            return expediente
        except Exception as e:
            raise Exception(f"Error en lógica de expediente: {str(e)}")
    
    async def crear_documento(
        self,
        db: Session,
        expediente: T_Expediente,
        nombre_archivo: str,
        tipo_archivo: str,
        ruta_archivo: Optional[str] = None,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Lógica de negocio para crear documento.
        Valida datos del archivo y maneja estados iniciales.
        
        Args:
            db: Sesión de base de datos
            expediente: Expediente al que pertenece el documento
            nombre_archivo: Nombre del archivo
            tipo_archivo: Tipo/extensión del archivo
            ruta_archivo: Ruta donde se guardó el archivo (opcional)
            auto_commit: Si hacer commit automático
            
        Returns:
            T_Documento: Documento creado
            
        Raises:
            Exception: Si hay error en validaciones o creación
        """
        # Validaciones de negocio
        if not nombre_archivo or not nombre_archivo.strip():
            raise Exception("El nombre del archivo no puede estar vacío")
        
        if not tipo_archivo or not tipo_archivo.strip():
            raise Exception("El tipo de archivo no puede estar vacío")
        
        # Validar extensión permitida (usar configuración centralizada)
        if not any(tipo_archivo.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            # Mensaje amigable para el usuario sin lista completa
            raise Exception(f"El formato {tipo_archivo} no es compatible. Use PDF, Word, audio (MP3/WAV) o texto.")
        
        try:
            # Obtener estado inicial "Pendiente"
            estado_pendiente = await self.obtener_estado_procesamiento(db, "Pendiente")
            
            # Crear documento usando repository
            documento = self.documento_repo.crear(
                db=db,
                expediente=expediente,
                nombre_archivo=nombre_archivo.strip(),
                tipo_archivo=tipo_archivo.strip(),
                estado_procesamiento=estado_pendiente,
                ruta_archivo=ruta_archivo,
                auto_commit=auto_commit
            )
            
            print(f"Documento creado: {documento.CT_Nombre_archivo}")
            return documento
            
        except Exception as e:
            raise Exception(f"Error en lógica de documento: {str(e)}")
    
    async def actualizar_estado_documento(
        self,
        db: Session,
        documento: T_Documento,
        nuevo_estado: str,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Lógica de negocio para actualizar estado de documento.
        Valida transiciones de estado permitidas.
        
        Args:
            db: Sesión de base de datos
            documento: Documento a actualizar
            nuevo_estado: Nuevo estado ('Pendiente', 'Procesado', 'Error')
            auto_commit: Si hacer commit automático
            
        Returns:
            T_Documento: Documento actualizado
            
        Raises:
            Exception: Si hay error en validaciones o actualización
        """
        # Validaciones de negocio
        estados_permitidos = ['Pendiente', 'Procesado', 'Error']
        if nuevo_estado not in estados_permitidos:
            raise Exception(f"Estado '{nuevo_estado}' no es válido. Estados permitidos: {estados_permitidos}")
        
        try:
            # Obtener el nuevo estado
            estado = await self.obtener_estado_procesamiento(db, nuevo_estado)
            
            # Actualizar usando repository
            documento_actualizado = self.documento_repo.actualizar_estado(
                db=db,
                documento=documento,
                nuevo_estado=estado,
                auto_commit=auto_commit
            )
            
            print(f"Estado actualizado a '{nuevo_estado}' para: {documento.CT_Nombre_archivo}")
            return documento_actualizado
            
        except Exception as e:
            raise Exception(f"Error en lógica de actualización de estado: {str(e)}")
    
    async def actualizar_ruta_documento(
        self,
        db: Session,
        documento: T_Documento,
        ruta_archivo: str,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Lógica de negocio para actualizar ruta de archivo.
        Valida que la ruta sea válida y el archivo exista.
        
        Args:
            db: Sesión de base de datos
            documento: Documento a actualizar
            ruta_archivo: Nueva ruta del archivo
            auto_commit: Si hacer commit automático
            
        Returns:
            T_Documento: Documento actualizado
        """
        # Validaciones de negocio
        if not ruta_archivo or not ruta_archivo.strip():
            raise Exception("La ruta del archivo no puede estar vacía")
        
        # Validar que la ruta sea válida (formato)
        ruta_path = Path(ruta_archivo)
        if not ruta_path.suffix:
            raise Exception("La ruta debe incluir una extensión de archivo")
        
        try:
            # Actualizar usando repository
            documento_actualizado = self.documento_repo.actualizar_ruta_archivo(
                db=db,
                documento=documento,
                ruta_archivo=ruta_archivo.strip(),
                auto_commit=auto_commit
            )
            
            print(f"Ruta actualizada para: {documento.CT_Nombre_archivo}")
            return documento_actualizado
            
        except Exception as e:
            raise Exception(f"Error en lógica de actualización de ruta: {str(e)}")
    
    async def listar_documentos_expediente(self, db: Session, numero_expediente: str) -> List[T_Documento]:
        """
        Lógica de negocio para listar documentos de expediente.
        Valida que el expediente exista.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            List[T_Documento]: Lista de documentos del expediente
        """
        # Validaciones de negocio
        if not numero_expediente or not numero_expediente.strip():
            raise Exception("El número de expediente no puede estar vacío")
        
        try:
            # Buscar expediente
            expediente = self.expediente_repo.obtener_por_numero(db, numero_expediente.strip())
            
            if not expediente:
                return []  # Expediente no existe, retornar lista vacía
            
            # Listar documentos usando repository
            documentos = self.documento_repo.listar_por_expediente(db, expediente)
            
            return documentos
            
        except Exception as e:
            raise Exception(f"Error en lógica de listado de documentos: {str(e)}")
    
    async def obtener_documento_por_id(self, db: Session, documento_id: int) -> Optional[T_Documento]:
        """
        Lógica de negocio para obtener documento por ID.
        Valida que el ID sea válido.
        
        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            Optional[T_Documento]: Documento encontrado o None
        """
        # Validaciones de negocio
        if documento_id <= 0:
            raise Exception("El ID del documento debe ser un número positivo")
        
        try:
            # Obtener usando repository
            documento = self.documento_repo.obtener_por_id(db, documento_id)
            
            return documento
            
        except Exception as e:
            raise Exception(f"Error en lógica de obtención de documento: {str(e)}")
