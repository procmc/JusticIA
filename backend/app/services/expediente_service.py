from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.database import get_db
from app.db.models.expediente import T_Expediente
from app.db.models.documento import T_Documento
from app.db.models.estado_procesamiento import T_Estado_procesamiento
from datetime import datetime
from typing import Optional
import os
from pathlib import Path
from fastapi import UploadFile

class ExpedienteService:
    """Servicio para manejar operaciones de expedientes y documentos"""
    
    @staticmethod
    async def obtener_estado_procesamiento(db: Session, nombre_estado: str) -> T_Estado_procesamiento:
        """
        Obtiene un estado de procesamiento por su nombre.
        
        Args:
            db: Sesión de base de datos
            nombre_estado: Nombre del estado ('Pendiente', 'Procesado', 'Error')
            
        Returns:
            T_Estado_procesamiento: Estado encontrado
            
        Raises:
            Exception: Si no se encuentra el estado
        """
        stmt = select(T_Estado_procesamiento).where(T_Estado_procesamiento.CT_Nombre_estado == nombre_estado)
        result = db.execute(stmt)
        estado = result.scalar_one_or_none()
        
        if not estado:
            raise Exception(f"Estado de procesamiento '{nombre_estado}' no encontrado")
        
        return estado
    
    @staticmethod
    async def buscar_o_crear_expediente(db: Session, numero_expediente: str) -> T_Expediente:
        """
        Busca un expediente existente o crea uno nuevo.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            T_Expediente: Expediente encontrado o creado
        """
        # Buscar expediente existente
        stmt = select(T_Expediente).where(T_Expediente.CT_Num_expediente == numero_expediente)
        result = db.execute(stmt)
        expediente = result.scalar_one_or_none()
        
        # Si no existe, crear uno nuevo
        if not expediente:
            expediente = T_Expediente(
                CT_Num_expediente=numero_expediente,
                CF_Fecha_creacion=datetime.utcnow()
            )
            db.add(expediente)
            db.commit()
            db.refresh(expediente)
            
        return expediente
    
    @staticmethod
    async def crear_documento(
        db: Session, 
        expediente: T_Expediente, 
        nombre_archivo: str, 
        tipo_archivo: str,
        ruta_archivo: str = None,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Crea un nuevo documento asociado a un expediente.
        
        Args:
            db: Sesión de base de datos
            expediente: Expediente al que pertenece el documento
            nombre_archivo: Nombre del archivo
            tipo_archivo: Tipo de archivo (extensión)
            ruta_archivo: Ruta donde se almacena el archivo (opcional)
            auto_commit: Si debe hacer commit automático (False para transacciones externas)
            
        Returns:
            T_Documento: Documento creado
            
        Raises:
            Exception: Si hay error en la operación
        """
        try:
            # Obtener el estado "Pendiente" para el documento recién creado
            estado_pendiente = await ExpedienteService.obtener_estado_procesamiento(db, "Pendiente")
            
            # Iniciar transacción si es necesario
            documento = T_Documento(
                CT_Nombre_archivo=nombre_archivo,
                CT_Tipo_archivo=tipo_archivo,
                CT_Ruta_archivo=ruta_archivo,
                CF_Fecha_carga=datetime.utcnow(),
                CN_Id_estado=estado_pendiente.CN_Id_estado  # Asignar estado "Pendiente"
            )
            
            # Asociar con el expediente
            expediente.documentos.append(documento)
            
            # Guardar en la base de datos
            db.add(documento)
            db.flush()  # Flush para obtener el ID sin commit
            
            # Hacer commit solo si se especifica
            if auto_commit:
                db.commit()
                db.refresh(documento)
            
            return documento
            
        except Exception as e:
            # Si hay error y auto_commit está activado, hacer rollback
            if auto_commit:
                db.rollback()
            raise Exception(f"Error creando documento: {str(e)}")
    
    @staticmethod
    async def actualizar_estado_documento(
        db: Session, 
        documento: T_Documento, 
        nuevo_estado: str,
        auto_commit: bool = True
    ) -> T_Documento:
        """
        Actualiza el estado de procesamiento de un documento.
        
        Args:
            db: Sesión de base de datos
            documento: Documento a actualizar
            nuevo_estado: Nuevo estado ('Pendiente', 'Procesado', 'Error')
            auto_commit: Si debe hacer commit automático
            
        Returns:
            T_Documento: Documento actualizado
            
        Raises:
            Exception: Si hay error en la operación
        """
        try:
            # Obtener el nuevo estado
            estado = await ExpedienteService.obtener_estado_procesamiento(db, nuevo_estado)
            
            # Actualizar el estado del documento
            documento.CN_Id_estado = estado.CN_Id_estado
            
            db.add(documento)
            
            if auto_commit:
                db.commit()
                db.refresh(documento)
            
            return documento
            
        except Exception as e:
            if auto_commit:
                db.rollback()
            raise Exception(f"Error actualizando estado del documento: {str(e)}")
    
    @staticmethod
    async def listar_documentos_expediente(db: Session, numero_expediente: str) -> list[T_Documento]:
        """
        Lista todos los documentos de un expediente específico.
        
        Args:
            db: Sesión de base de datos
            numero_expediente: Número del expediente
            
        Returns:
            list[T_Documento]: Lista de documentos del expediente
        """
        # Buscar expediente
        stmt = select(T_Expediente).where(T_Expediente.CT_Num_expediente == numero_expediente)
        result = db.execute(stmt)
        expediente = result.scalar_one_or_none()
        
        if not expediente:
            return []
        
        return expediente.documentos
    
    @staticmethod
    async def obtener_documento_por_id(db: Session, documento_id: int) -> Optional[T_Documento]:
        """
        Obtiene un documento específico por su ID.
        
        Args:
            db: Sesión de base de datos
            documento_id: ID del documento
            
        Returns:
            T_Documento: Documento encontrado o None
        """
        stmt = select(T_Documento).where(T_Documento.CN_Id_documento == documento_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()
