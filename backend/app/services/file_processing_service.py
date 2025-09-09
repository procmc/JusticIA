import os
import uuid
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
import filetype

from app.schemas.schemas import (
    FileUploadResponse, 
    FileValidationError, 
    FileProcessingStatus,
    ArchivoSimplificado
)
from app.config.file_config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from app.vectorstore.milvus_storage import store_in_vectorstore
from app.services.expediente_service import ExpedienteService
from app.services.file_storage_service import FileStorageService
from app.services.transaction_service import TransactionManager
from app.db.database import get_db

async def process_uploaded_files(files: List[UploadFile], CT_Num_expediente: str, db: Optional[Session] = None) -> FileProcessingStatus:
    """
    Procesa una lista de archivos subidos para un expediente específico.
    Solo almacena en vectorstore si se puede crear registro en BD (transaccional).
    
    Args:
        files: Lista de archivos a procesar
        CT_Num_expediente: Número de expediente validado
        db: Sesión de BD (requerida para almacenamiento completo)
        
    Returns:
        FileProcessingStatus: Estado del procesamiento con detalles
    """
    archivos_procesados = []
    archivos_con_error = []
    
    # 1. Buscar o crear expediente en BD (requerido para almacenamiento)
    if db:
        try:
            expediente_service = ExpedienteService()
            expediente = await expediente_service.buscar_o_crear_expediente(db, CT_Num_expediente)
            print(f"Expediente obtenido/creado: {expediente.CT_Num_expediente}")
        except Exception as e:
            print(f"Error BD - procesamiento sin almacenamiento: {str(e)}")
            expediente = None
    else:
        print(f"Sin sesión BD - procesamiento sin almacenamiento")
        expediente = None
    
    # 2. Procesar cada archivo (solo se almacena en vectorstore si hay BD)
    for file in files:
        try:
            # Validar archivo
            validation_error = validate_file(file)
            if validation_error:
                archivos_con_error.append(validation_error)
                continue
            
            # Procesar archivo con lógica transaccional
            result = await process_single_file(file, CT_Num_expediente, expediente, db)
            archivos_procesados.append(result)
            
        except Exception as e:
            error = FileValidationError(
                error="Error de procesamiento",
                archivo=file.filename or "archivo_sin_nombre",
                razon=str(e),
                formatos_permitidos=ALLOWED_EXTENSIONS
            )
            archivos_con_error.append(error)
    
    return FileProcessingStatus(
        total_archivos=len(files),
        procesados_exitosamente=len(archivos_procesados),
        errores=len(archivos_con_error),
        archivos_procesados=archivos_procesados,
        archivos_con_error=archivos_con_error
    )


def generar_respuesta_simplificada(resultado_completo: FileProcessingStatus, expediente: str):
    """
    Genera una respuesta simplificada con solo la información esencial.
    
    Args:
        resultado_completo: Resultado completo del procesamiento
        expediente: Número de expediente
        
    Returns:
        dict: Respuesta simplificada compatible con IngestaArchivosResponse
    """
    from app.schemas.ingesta_schemas import IngestaArchivosResponse
    
    archivos_simplificados = []
    
    # Procesar archivos exitosos
    for archivo in resultado_completo.archivos_procesados:
        documento_id = None
        if archivo.metadatos and "documento_id" in archivo.metadatos:
            documento_id = archivo.metadatos["documento_id"]
        
        archivo_simple = ArchivoSimplificado(
            status="success",
            nombre_archivo=archivo.nombre_archivo,
            documento_id=documento_id,
            mensaje="Procesado y almacenado exitosamente"
        )
        archivos_simplificados.append(archivo_simple)
    
    # Procesar archivos con error
    for error in resultado_completo.archivos_con_error:
        archivo_simple = ArchivoSimplificado(
            status="error",
            nombre_archivo=error.archivo,
            documento_id=None,
            error=f"{error.error}: {error.razon}"
        )
        archivos_simplificados.append(archivo_simple)
    
    return IngestaArchivosResponse(
        expediente=expediente,
        total_archivos=resultado_completo.total_archivos,
        archivos_exitosos=resultado_completo.procesados_exitosamente,
        archivos_fallidos=resultado_completo.errores,
        archivos=archivos_simplificados
    )

def validate_file(file: UploadFile) -> FileValidationError | None:
    """
    Valida un archivo subido según los criterios establecidos.
    """
    # Validar nombre de archivo
    if not file.filename:
        return FileValidationError(
            error="Archivo inválido",
            archivo="sin_nombre",
            razon="El archivo debe tener un nombre",
            formatos_permitidos=ALLOWED_EXTENSIONS
        )
    
    # Validar extensión
    file_path = Path(file.filename)
    extension = file_path.suffix.lower()
    
    if extension not in ALLOWED_EXTENSIONS:
        return FileValidationError(
            error="Formato no permitido",
            archivo=file.filename,
            razon=f"Extensión '{extension}' no está permitida",
            formatos_permitidos=ALLOWED_EXTENSIONS
        )
    
    # Validar content type
    if file.content_type and file.content_type not in ALLOWED_FILE_TYPES:
        return FileValidationError(
            error="Tipo MIME no permitido",
            archivo=file.filename,
            razon=f"Tipo MIME '{file.content_type}' no está permitido",
            formatos_permitidos=ALLOWED_EXTENSIONS
        )
    
    # Validar tamaño (si está disponible)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        size_mb = file.size / (1024 * 1024)
        return FileValidationError(
            error="Archivo demasiado grande",
            archivo=file.filename,
            razon=f"El archivo ({size_mb:.1f}MB) excede el límite de {MAX_FILE_SIZE / (1024 * 1024)}MB",
            formatos_permitidos=ALLOWED_EXTENSIONS
        )
    
    return None

async def process_single_file(file: UploadFile, CT_Num_expediente: str, expediente=None, db: Optional[Session] = None) -> FileUploadResponse:
    """
    Procesa un solo archivo usando transacciones atómicas con TransactionManager.
    Garantiza consistencia entre BD, almacenamiento físico y vectorstore.
    """
    file_id = str(uuid.uuid4())
    
    try:
        # Validar nombre de archivo primero
        if not file.filename:
            raise ValueError("El archivo debe tener un nombre")
        
        # Leer contenido del archivo
        content = await file.read()
        
        # Detectar tipo de archivo usando filetype
        detected_type = filetype.guess(content)
        tipo_archivo = detected_type.mime if detected_type else file.content_type or "application/octet-stream"
        
        # Extraer texto según el tipo
        texto_extraido = await extract_text_from_file(content, file.filename, tipo_archivo)
        
        if not texto_extraido.strip():
            raise ValueError("No se pudo extraer texto del archivo")
        
        # Inicializar variables
        ruta_archivo = None
        metadatos = {
            "file_id": file_id,
            "nombre_archivo": file.filename,
            "tipo_archivo": tipo_archivo,
            "expediente": CT_Num_expediente,
            "fecha_procesamiento": datetime.now().isoformat(),
            "tamaño_archivo": len(content)
        }
        
        # ============ PROCESAMIENTO CON BD (TRANSACCIONAL) ============
        if expediente and db:
            documento_creado = None
            expediente_service = ExpedienteService()
            
            try:
                # 1. Crear documento en BD con estado "Pendiente" (sin commit)
                extension = Path(file.filename).suffix.lower()
                documento_creado = await expediente_service.crear_documento(
                    db=db,
                    expediente=expediente,
                    nombre_archivo=file.filename,
                    tipo_archivo=extension,
                    ruta_archivo="",  # Se actualiza después
                    auto_commit=False  # No hacer commit automático
                )
                print(f"Documento creado en BD con estado 'Pendiente': {documento_creado.CT_Nombre_archivo}")
                
                # 2. Guardar archivo físicamente
                storage = FileStorageService()
                ruta_archivo = await storage.guardar_archivo(file, CT_Num_expediente)
                print(f"Archivo guardado físicamente: {ruta_archivo}")
                
                # 3. Actualizar la ruta en el documento
                await expediente_service.actualizar_ruta_documento(
                    db=db,
                    documento=documento_creado,
                    ruta_archivo=ruta_archivo,
                    auto_commit=False
                )
                print(f"Ruta actualizada en documento")
                
                # 4. Actualizar metadatos con info de BD
                metadatos.update({
                    "documento_id": documento_creado.CN_Id_documento,  # Usar el nombre correcto del campo
                    "ruta_archivo": ruta_archivo
                })
                
                # 5. Almacenar en Milvus con IDs reales
                await store_in_vectorstore(
                    texto=texto_extraido, 
                    metadatos=metadatos, 
                    CT_Num_expediente=CT_Num_expediente,
                    id_expediente=expediente.CN_Id_expediente,  # ID real del expediente
                    id_documento=documento_creado.CN_Id_documento  # ID real del documento
                )
                print(f"Almacenado en vectorstore exitosamente")
                
                # 6. Actualizar estado a "Procesado" si todo salió bien
                await expediente_service.actualizar_estado_documento(
                    db=db,
                    documento=documento_creado,
                    nuevo_estado="Procesado",
                    auto_commit=False  # No hacer commit aún
                )
                print(f"Estado actualizado a 'Procesado'")
                
                # 7. Si todo salió bien, hacer commit final
                db.commit()
                db.refresh(documento_creado)
                print(f"Transacción completada exitosamente")
                
            except Exception as e:
                # Rollback en caso de error y actualizar estado a "Error"
                print(f"Error en transacción: {str(e)}")
                try:
                    # Si tenemos el documento creado, actualizar su estado a "Error"
                    if documento_creado:
                        await expediente_service.actualizar_estado_documento(
                            db=db,
                            documento=documento_creado,
                            nuevo_estado="Error",
                            auto_commit=False
                        )
                        print(f"Estado actualizado a 'Error'")
                        db.commit()  # Commit solo el cambio de estado
                    else:
                        db.rollback()  # Rollback completo si no hay documento
                    print("Rollback de BD realizado")
                except Exception as rollback_error:
                    print(f"Error en rollback: {str(rollback_error)}")
                    db.rollback()  # Rollback de emergencia
                
                # Re-lanzar la excepción original
                raise e
        
        else:
            # Sin BD disponible - NO almacenar en Milvus
            print(f"No se almacena en vectorstore: requiere transacción de BD exitosa")
            metadatos.update({"status": "procesado_sin_bd"})

        # Reiniciar posición del archivo para futuras operaciones
        await file.seek(0)
        
        # Determinar mensaje según si hubo transacción completa
        if expediente and db:
            message = "Archivo procesado exitosamente con transacciones atómicas"
        else:
            message = "Archivo procesado SIN almacenamiento (requiere BD para vectorstore)"
        
        return FileUploadResponse(
            status="success",
            message=message,
            file_id=file_id,
            expediente=CT_Num_expediente,
            nombre_archivo=file.filename,
            tipo_archivo=tipo_archivo,
            fecha_procesamiento=datetime.now(),
            texto_extraido_preview=texto_extraido[:200] + "..." if len(texto_extraido) > 200 else texto_extraido,
            metadatos=metadatos
        )
        
    except Exception as e:
        print(f"Error en procesamiento de archivo: {str(e)}")
        return FileUploadResponse(
            status="error",
            message="Error procesando archivo (transacciones revertidas)",
            file_id=file_id,
            expediente=CT_Num_expediente,
            nombre_archivo=file.filename,
            tipo_archivo=file.content_type or "unknown",
            fecha_procesamiento=datetime.now(),
            error_detalle=str(e)
        )

async def extract_text_from_file(content: bytes, filename: str, content_type: str) -> str:
    """
    Extrae texto de diferentes tipos de archivos:
    - MP3: Transcripción con Whisper
    - Otros formatos (PDF, DOC, DOCX, RTF, TXT, etc.): Apache Tika
    """
    file_extension = Path(filename).suffix.lower()
    
    # Archivos de audio se procesan con Whisper
    if file_extension == '.mp3':
        return await extract_text_from_audio_whisper(content, filename)
    
    # Los demás formatos con Tika
    try:
        from tika import parser
        
        # Tika procesa automáticamente cualquier formato soportado
        parsed = parser.from_buffer(content)
        
        # Extraer el texto - Tika devuelve un dict
        if not isinstance(parsed, dict):
            raise ValueError("Respuesta inesperada de Tika")
            
        texto = parsed.get('content', '') or ''
        
        if not texto or not texto.strip():
            raise ValueError("No se pudo extraer texto del archivo")
        
        # Limpiar el texto (remover espacios excesivos, saltos de línea múltiples)
        texto_limpio = ' '.join(texto.split())
        
        return texto_limpio
        
    except ImportError:
        raise ValueError("Apache Tika no está disponible. Verificar instalación de Java y Tika.")
    except Exception as e:
        raise ValueError(f"Error extrayendo texto de {filename}: {str(e)}")

async def extract_text_from_audio_whisper(content: bytes, filename: str) -> str:
    """
    Transcribe audio MP3 usando faster-whisper optimizado.
    Sistema secuencial inteligente: intenta directo primero, chunks si es necesario.
    """
    try:
        from app.services.audio_chunk_service import audio_processor
        from app.config.audio_config import AUDIO_CONFIG
        
        # Log de configuración
        file_size_mb = len(content) / (1024 * 1024)
        print(f"Procesando audio {filename}: {file_size_mb:.1f} MB")
        print(f"Configuración: modelo={AUDIO_CONFIG.whisper_model}, device={AUDIO_CONFIG.device}")
        print(f"faster-whisper: compute_type={AUDIO_CONFIG.compute_type}, workers={AUDIO_CONFIG.num_workers}")
        print(f"Chunks si archivo >= {AUDIO_CONFIG.enable_chunking_threshold_mb} MB o falla directo")
        print(f"Procesamiento: SECUENCIAL OPTIMIZADO (sin paralelismo)")
        
        # Usar el procesador de audio optimizado
        texto = await audio_processor.transcribe_audio_direct(content, filename)
        
        if not texto.strip():
            raise ValueError("No se pudo transcribir el audio")
        
        print(f"Transcripción completada: {len(texto)} caracteres")
        return texto
        
    except ImportError:
        raise ValueError("OpenAI Whisper no está disponible. Instalar con 'pip install openai-whisper'")
    except Exception as e:
        raise ValueError(f"Error transcribiendo audio {filename}: {str(e)}")
