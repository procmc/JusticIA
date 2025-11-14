"""
Campos Estandarizados de Metadata para Vectorstore y Base de Datos.

Este módulo es la **FUENTE ÚNICA DE VERDAD** para nombres de campos de metadata
en todo el sistema de almacenamiento vectorial (Milvus) y base de datos (SQL Server).

Propósito:
    - Centralizar nombres de campos para evitar typos y bugs
    - Facilitar refactorización y renombrado de campos
    - Documentar convenciones de nomenclatura
    - Proporcionar mapeo bidireccional BD ↔ Vectorstore

Componentes principales:
    1. MetadataFields: Campos en Milvus (snake_case)
    2. DatabaseFields: Campos en SQL Server (prefijos CT_/CN_)
    3. FieldMapper: Mapeo bidireccional y conversión de diccionarios

Arquitectura de datos:
    ```
    SQL Server (T_Documento)     Milvus Vectorstore
    ========================     ==================
    CT_Num_expediente      →     expediente_numero
    CN_Id_documento        →     id_documento
    CT_Nombre_archivo      →     archivo
    CT_Ruta_archivo        →     ruta_archivo
    ```

Convenciones de nomenclatura:
    **Vectorstore (MetadataFields):**
        - snake_case (estándar Python/backend)
        - Prefijos descriptivos: expediente_, documento_, chunk_
        - Sin prefijos de BD (CT_/CN_)
        - Legible y auto-documentado
    
    **Base de Datos (DatabaseFields):**
        - CamelCase con guiones bajos
        - Prefijos: CT_ (texto), CN_ (número), CF_ (fecha)
        - Consistente con esquema SQL Server existente

Uso del FieldMapper:
    Conversión automática entre formatos BD y vectorstore:
    ```python
    # BD → Vectorstore
    db_data = {"CT_Num_expediente": "2022-003287-0166-LA"}
    vector_data = FieldMapper.map_db_to_vector(db_data)
    # → {"expediente_numero": "2022-003287-0166-LA"}
    
    # Vectorstore → BD
    vector_data = {"expediente_numero": "2022-003287-0166-LA"}
    db_data = FieldMapper.map_vector_to_db(vector_data)
    # → {"CT_Num_expediente": "2022-003287-0166-LA"}
    ```

Example:
    ```python
    from app.constants.metadata_fields import MF, DF, FM
    
    # Usar constantes en lugar de strings
    metadata = {
        MF.EXPEDIENTE_NUMERO: '2022-003287-0166-LA',
        MF.DOCUMENTO_NOMBRE: 'demanda.pdf',
        MF.CHUNK_INDEX: 0,
        MF.SIMILARITY_SCORE: 0.85
    }
    
    # Mapear diccionario completo
    db_dict = {
        DF.EXPEDIENTE_NUMERO: '2022-003287-0166-LA',
        DF.DOCUMENTO_NOMBRE: 'demanda.pdf'
    }
    vector_dict = FM.map_db_to_vector(db_dict)
    
    # Conversión individual
    vector_field = FM.db_to_vector(DF.EXPEDIENTE_NUMERO)
    # → 'expediente_numero'
    ```

Note:
    Cualquier cambio en nombres de campos debe:
        1. Actualizarse en este módulo
        2. Propagarse a Milvus (recrear colección si es necesario)
        3. Actualizarse en migraciones de BD si aplica
        4. Actualizar mapeos en FieldMapper

See Also:
    - app.vectorstore: Usa MetadataFields para estructura de metadata
    - app.services.similarity_service: Usa FieldMapper para convertir resultados
    - app.embeddings: Usa MetadataFields al crear embeddings
    - tasks.procesar_ingesta: Usa MetadataFields al ingestar documentos
"""

class MetadataFields:
    """
    Nombres estandarizados de campos en metadata de documentos vectorizados.
    
    CONVENCIÓN:
    - Usar snake_case (Python/backend estándar)
    - Prefijos descriptivos (expediente_, documento_, chunk_)
    - Sin prefijos CT_/CN_ (esos son para BD, aquí es vectorstore)
    """
    
    # ===== EXPEDIENTE =====
    EXPEDIENTE_NUMERO = "expediente_numero"
    """Número de expediente (ej: '2022-003287-0166-LA')"""
    
    EXPEDIENTE_ID = "expediente_id"
    """ID único del expediente (puede ser UUID o int)"""
    
    # ===== DOCUMENTO =====
    DOCUMENTO_ID = "id_documento"
    """ID del documento en BD"""
    
    DOCUMENTO_NOMBRE = "archivo"
    """Nombre del archivo (ej: 'demanda.pdf')"""
    
    DOCUMENTO_RUTA = "ruta_archivo"
    """Ruta completa del archivo en filesystem"""
    
    DOCUMENTO_TIPO = "tipo_documento"
    """Tipo: 'document' o 'audio'"""
    
    # ===== CHUNK =====
    CHUNK_INDEX = "chunk_index"
    """Índice del chunk dentro del documento (0, 1, 2, ...)"""
    
    CHUNK_TOTAL = "total_chunks"
    """Total de chunks del documento"""
    
    # ===== SIMILITUD =====
    SIMILARITY_SCORE = "similarity_score"
    """Score de similitud (0.0 - 1.0) calculado por búsqueda"""
    
    # ===== METADATA ADICIONAL =====
    FECHA_INGESTA = "fecha_ingesta"
    """Timestamp de cuándo se ingresó el documento"""
    
    USUARIO_INGESTA = "usuario_ingesta"
    """Cédula del usuario que ingresó el documento"""


class DatabaseFields:
    """
    Nombres de campos en la base de datos SQL.
    
    CONVENCIÓN:
    - Usar prefijos CT_ (tipo texto) o CN_ (tipo número)
    - CamelCase con guiones bajos
    - Mantener consistencia con esquema BD existente
    """
    
    # ===== EXPEDIENTE =====
    EXPEDIENTE_ID = "CN_Id_expediente"
    EXPEDIENTE_NUMERO = "CT_Num_expediente"
    
    # ===== DOCUMENTO =====
    DOCUMENTO_ID = "CN_Id_documento"
    DOCUMENTO_NOMBRE = "CT_Nombre_archivo"
    DOCUMENTO_RUTA = "CT_Ruta_archivo"
    DOCUMENTO_TIPO = "CT_Tipo_documento"
    DOCUMENTO_ESTADO = "CT_Estado"
    
    # ===== USUARIO =====
    USUARIO_ID = "CN_Id_usuario"
    USUARIO_CEDULA = "CT_Cedula_usuario"
    USUARIO_NOMBRE = "CT_Nombre_usuario"


class FieldMapper:
    """
    Mapeo bidireccional entre campos de BD y Vectorstore.
    
    Uso:
        # BD → Vectorstore
        vector_field = FieldMapper.db_to_vector("CT_Num_expediente")
        # → "expediente_numero"
        
        # Vectorstore → BD  
        db_field = FieldMapper.vector_to_db("expediente_numero")
        # → "CT_Num_expediente"
    """
    
    # Mapeo BD → Vectorstore
    _DB_TO_VECTOR = {
        DatabaseFields.EXPEDIENTE_NUMERO: MetadataFields.EXPEDIENTE_NUMERO,
        DatabaseFields.EXPEDIENTE_ID: MetadataFields.EXPEDIENTE_ID,
        DatabaseFields.DOCUMENTO_ID: MetadataFields.DOCUMENTO_ID,
        DatabaseFields.DOCUMENTO_NOMBRE: MetadataFields.DOCUMENTO_NOMBRE,
        DatabaseFields.DOCUMENTO_RUTA: MetadataFields.DOCUMENTO_RUTA,
        DatabaseFields.DOCUMENTO_TIPO: MetadataFields.DOCUMENTO_TIPO,
        DatabaseFields.USUARIO_CEDULA: MetadataFields.USUARIO_INGESTA,
    }
    
    # Mapeo Vectorstore → BD (inverso)
    _VECTOR_TO_DB = {v: k for k, v in _DB_TO_VECTOR.items()}
    
    @classmethod
    def db_to_vector(cls, db_field: str) -> str:
        """
        Convierte nombre de campo BD a vectorstore.
        
        Args:
            db_field: Nombre del campo en BD (ej: 'CT_Num_expediente')
            
        Returns:
            Nombre del campo en vectorstore (ej: 'expediente_numero')
            
        Raises:
            KeyError: Si el campo no está mapeado
        """
        if db_field not in cls._DB_TO_VECTOR:
            raise KeyError(
                f"Campo BD '{db_field}' no tiene mapeo a vectorstore. "
                f"Campos disponibles: {list(cls._DB_TO_VECTOR.keys())}"
            )
        return cls._DB_TO_VECTOR[db_field]
    
    @classmethod
    def vector_to_db(cls, vector_field: str) -> str:
        """
        Convierte nombre de campo vectorstore a BD.
        
        Args:
            vector_field: Nombre del campo en vectorstore (ej: 'expediente_numero')
            
        Returns:
            Nombre del campo en BD (ej: 'CT_Num_expediente')
            
        Raises:
            KeyError: Si el campo no está mapeado
        """
        if vector_field not in cls._VECTOR_TO_DB:
            raise KeyError(
                f"Campo vectorstore '{vector_field}' no tiene mapeo a BD. "
                f"Campos disponibles: {list(cls._VECTOR_TO_DB.keys())}"
            )
        return cls._VECTOR_TO_DB[vector_field]
    
    @classmethod
    def map_db_to_vector(cls, db_dict: dict) -> dict:
        """
        Convierte diccionario completo de BD a formato vectorstore.
        
        Args:
            db_dict: Diccionario con campos BD
            
        Returns:
            Diccionario con campos vectorstore
            
        Example:
            >>> db_data = {
            ...     "CT_Num_expediente": "2022-003287-0166-LA",
            ...     "CT_Nombre_archivo": "demanda.pdf"
            ... }
            >>> FieldMapper.map_db_to_vector(db_data)
            {'expediente_numero': '2022-003287-0166-LA', 'archivo': 'demanda.pdf'}
        """
        result = {}
        for db_key, value in db_dict.items():
            try:
                vector_key = cls.db_to_vector(db_key)
                result[vector_key] = value
            except KeyError:
                # Mantener campos no mapeados tal cual (con warning)
                import logging
                logging.getLogger(__name__).debug(
                    f"Campo '{db_key}' no tiene mapeo, se mantiene original"
                )
                result[db_key] = value
        return result
    
    @classmethod
    def map_vector_to_db(cls, vector_dict: dict) -> dict:
        """
        Convierte diccionario completo de vectorstore a formato BD.
        
        Args:
            vector_dict: Diccionario con campos vectorstore
            
        Returns:
            Diccionario con campos BD
            
        Example:
            >>> vector_data = {
            ...     "expediente_numero": "2022-003287-0166-LA",
            ...     "archivo": "demanda.pdf"
            ... }
            >>> FieldMapper.map_vector_to_db(vector_data)
            {'CT_Num_expediente': '2022-003287-0166-LA', 'CT_Nombre_archivo': 'demanda.pdf'}
        """
        result = {}
        for vector_key, value in vector_dict.items():
            try:
                db_key = cls.vector_to_db(vector_key)
                result[db_key] = value
            except KeyError:
                # Mantener campos no mapeados tal cual (con warning)
                import logging
                logging.getLogger(__name__).debug(
                    f"Campo '{vector_key}' no tiene mapeo, se mantiene original"
                )
                result[vector_key] = value
        return result


# Aliases convenientes para importación
MF = MetadataFields
"""Alias corto: MetadataFields"""

DF = DatabaseFields
"""Alias corto: DatabaseFields"""

FM = FieldMapper
"""Alias corto: FieldMapper"""


# Export all
__all__ = [
    'MetadataFields',
    'DatabaseFields', 
    'FieldMapper',
    'MF',
    'DF',
    'FM'
]
