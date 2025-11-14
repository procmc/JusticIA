"""
Procesador principal de archivos con transacciones atómicas.

Maneja el procesamiento completo de archivos (PDF, audio, documentos) para expedientes,
incluyendo extracción de texto, limpieza, almacenamiento en BD y vectorstore con
transacciones atómicas.

Características:
    * Transacciones atómicas: BD + vectorstore (commit temprano)
    * Progress tracking: Sistema global con Redis
    * Cancelación: Verifica estado durante procesamiento
    * Validación: Extensiones, tamaño, tipo MIME
    * Routing: Audio→Whisper, PDF/docs→Tika, TXT→decode directo
    * Limpieza: Normalización Unicode y corrección encoding
    * Bitácora: Logging completo de operaciones
    * Error handling: Rollback BD si falla vectorstore

Flujo transaccional:
    1. Validar archivo (extensión, tamaño, tipo)
    2. Crear documento en BD con estado "Pendiente"
    3. Commit temprano (visibilidad inmediata)
    4. Extraer texto (Tika/Whisper según tipo)
    5. Limpiar texto (normalización + encoding)
    6. Almacenar en vectorstore (chunks + embeddings)
    7. Actualizar estado "Procesado" en BD
    8. Logging en bitácora (inicio/completado/error)

Commit temprano:
    * Documento visible aunque esté procesándose
    * Estado "Pendiente" durante procesamiento
    * Estado "Procesado" o "Error" al finalizar
    * Rollback BD si falla vectorstore (consistencia)

Progress tracking:
    * Actualización por archivo procesado
    * Porcentaje calculado: archivos_completados / total
    * Verificación de cancelación entre archivos
    * Mensajes informativos por fase

Example:
    >>> from app.services.ingesta.file_management.document_processor import process_uploaded_files
    >>> from app.schemas.schemas import FileProcessingStatus
    >>> 
    >>> # Procesar archivos
    >>> status = await process_uploaded_files(
    ...     files=[archivo1, archivo2],
    ...     CT_Num_expediente="00-000001-0001-PE",
    ...     db=db_session,
    ...     usuario_id="user_123",
    ...     progress_tracker=tracker,
    ...     cancel_check=lambda: check_cancelled()
    ... )
    >>> 
    >>> print(f"Éxito: {status.successful_files}, Error: {status.failed_files}")

Note:
    * Archivos quedan en disco aunque falle BD (auditoría)
    * Estado "Error" preserva información para debugging
    * Tika timeout 600s para PDFs con OCR
    * Whisper usa estrategias según tamaño
    * Validación de texto limpio (encoding, longitud)

Ver también:
    * app.services.ingesta.tika_service: Extracción PDF/docs
    * app.services.ingesta.audio_transcription.whisper_service: Transcripción audio
    * app.services.ingesta.text_cleaner: Limpieza de texto
    * app.services.ingesta.celery_tasks: Procesamiento asíncrono
    * app.vectorstore.milvus_storage: Almacenamiento vectorial

Authors:
    JusticIA Team

Version:
    2.0.0 - Transacciones atómicas con commit temprano
"""
import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
import filetype

logger = logging.getLogger(__name__)

from app.schemas.schemas import (
    FileUploadResponse, 
    FileValidationError, 
    FileProcessingStatus,
    ArchivoSimplificado
)
from app.config.file_config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from app.vectorstore.milvus_storage import store_in_vectorstore
from app.services.expediente_service import ExpedienteService
from app.services.documentos.file_management_service import file_management_service
from app.services.transaction_service import TransactionManager
from app.db.database import get_db
from ..async_processing.progress_tracker import ProgressTracker
from ..tika_service import TikaService
from .text_cleaner import clean_extracted_text, validate_cleaned_text, detect_encoding_problems

async def process_uploaded_files(
    files: List[UploadFile], 
    CT_Num_expediente: str, 
    db: Optional[Session] = None, 
    usuario_id: Optional[str] = None,
    progress_tracker: Optional[ProgressTracker] = None, 
    cancel_check: Optional[callable] = None
) -> FileProcessingStatus:
    """
    Procesa una lista de archivos subidos para un expediente específico.
    Solo almacena en vectorstore si se puede crear registro en BD (transaccional).
    
    Args:
        files: Lista de archivos a procesar
        CT_Num_expediente: Número de expediente validado
        db: Sesión de BD (requerida para almacenamiento completo)
        usuario_id: ID del usuario que inició la ingesta (para bitácora)
        progress_tracker: Tracker para reportar progreso granular
        cancel_check: Función opcional para verificar si se canceló la tarea
        
    Returns:
        FileProcessingStatus: Estado del procesamiento con detalles
    """
    archivos_procesados = []
    archivos_con_error = []
    
    # Verificar cancelación al inicio
    if cancel_check:
        cancel_check()
    
    # Progreso: Inicio (5%)
    if progress_tracker:
        filename = files[0].filename if files else "archivo"
        progress_tracker.update_progress(5, f"Iniciando procesamiento de {filename}")
    
    # Verificar cancelación
    if cancel_check:
        cancel_check()
    
    # Progreso: Preparación (10%)
    if progress_tracker:
        progress_tracker.update_progress(10, "Preparando entorno de procesamiento")
    
    # 1. Buscar o crear expediente en BD (requerido para almacenamiento)
    if db:
        try:
            # Verificar cancelación
            if cancel_check:
                cancel_check()
            
            # Progreso: Verificando expediente (15%)
            if progress_tracker:
                progress_tracker.update_progress(15, f"Verificando expediente {CT_Num_expediente}")
            
            expediente_service = ExpedienteService()
            expediente = await expediente_service.buscar_o_crear_expediente(db, CT_Num_expediente)
        except Exception as e:
            logger.warning(f"Error BD - procesamiento sin almacenamiento: {str(e)}")
            expediente = None
    else:
        logger.info(f"Sin sesión BD - procesamiento sin almacenamiento")
        expediente = None
    
    # Verificar cancelación
    if cancel_check:
        cancel_check()
    
    # Progreso: Listo para procesar (20%)
    if progress_tracker:
        progress_tracker.update_progress(20, "Iniciando procesamiento del archivo")
    
    # 2. Procesar cada archivo (solo se almacena en vectorstore si hay BD)
    for file in files:
        try:
            # Verificar cancelación antes de cada archivo
            if cancel_check:
                cancel_check()
            
            # Validar archivo
            validation_error = validate_file(file)
            if validation_error:
                # Registrar error de validación en bitácora
                if db and usuario_id:
                    try:
                        from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as bitacora_service
                        import asyncio
                        # Generar un task_id ficticio para tracking (no hay tarea Celery en validación)
                        task_id_validation = f"validation-{file.filename}-{id(file)}"
                        await bitacora_service.registrar_ingesta(
                            db, usuario_id, CT_Num_expediente, file.filename,
                            task_id_validation, "error", error_details=validation_error.razon
                        )
                    except Exception as bitacora_error:
                        logger.warning(f"No se pudo registrar error de validación en bitácora: {bitacora_error}")
                
                archivos_con_error.append(validation_error)
                continue
            
            # Procesar archivo con lógica transaccional
            # Para compatibilidad, leer el archivo aquí también
            content = await file.read()
            await file.seek(0)  # Reset para otras operaciones
            
            # Usar el nombre del archivo como ruta temporal (esto será mejorado)
            temp_filepath = f"uploads/{CT_Num_expediente}/{file.filename}"
            
            result = await process_single_file_with_content(
                file, content, temp_filepath, CT_Num_expediente, expediente, db, usuario_id, progress_tracker, cancel_check
            )
            archivos_procesados.append(result)
            
        except Exception as e:
            # Si es una excepción de cancelación, propagarla inmediatamente
            if "cancelada" in str(e).lower() or "terminated" in str(e).lower():
                logger.info(f"Error en procesamiento de archivo: {str(e)}")
                raise  # Propagar la excepción de cancelación
            
            # Para otros errores, registrarlos con el mensaje original
            error_msg = str(e)
            # Limpiar mensajes encadenados (evitar "Error procesando archivo (transacciones revertidas): mensaje")
            if "Error procesando archivo (transacciones revertidas):" in error_msg:
                error_msg = error_msg.split("Error procesando archivo (transacciones revertidas):")[-1].strip()
            
            error = FileValidationError(
                error=error_msg,  # Usar mensaje original como error principal
                archivo=file.filename or "archivo_sin_nombre",
                razon=error_msg,  # Mantener consistencia
                formatos_permitidos=ALLOWED_EXTENSIONS
            )
            archivos_con_error.append(error)
    
    # Progreso: Finalizado (100%)
    if progress_tracker and archivos_procesados:
        progress_tracker.mark_completed("Archivo procesado exitosamente")
    elif progress_tracker and archivos_con_error:
        error_msg = archivos_con_error[0].razon if archivos_con_error else "Error desconocido"
        progress_tracker.mark_failed(f"Error: {error_msg}")
    
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

async def process_single_file_with_content(
    file: UploadFile, 
    content: bytes, 
    filepath: str, 
    CT_Num_expediente: str, 
    expediente=None, 
    db: Optional[Session] = None,
    usuario_id: Optional[str] = None,
    progress_tracker: Optional[ProgressTracker] = None,
    cancel_check: Optional[callable] = None
) -> FileUploadResponse:
    """
    Procesa un solo archivo que ya fue guardado en disco.
    Garantiza consistencia entre BD y vectorstore.
    
    Args:
        file: Objeto UploadFile (para metadata)
        content: Contenido del archivo ya leído
        filepath: Ruta donde ya fue guardado el archivo
        CT_Num_expediente: Número del expediente
        expediente: Objeto expediente (opcional)
        db: Sesión de BD (opcional)
        usuario_id: ID del usuario que inició la ingesta (para bitácora)
        progress_tracker: Tracker de progreso (opcional)
        cancel_check: Función para verificar cancelación (opcional)
    """
    file_id = str(uuid.uuid4())
    
    try:
        # Verificar cancelación al inicio
        if cancel_check:
            cancel_check()
        
        # Validar nombre de archivo primero
        if not file.filename:
            raise ValueError("El archivo debe tener un nombre")
        
        # Progreso: Inicio del procesamiento (25%)
        if progress_tracker:
            progress_tracker.update_progress(25, f"Extrayendo texto de {file.filename}")
        
        # Verificar cancelación
        if cancel_check:
            cancel_check()
        
        # Detectar tipo de archivo usando filetype
        detected_type = filetype.guess(content)
        tipo_archivo = detected_type.mime if detected_type else file.content_type or "application/octet-stream"
        
        # Extraer texto según el tipo
        texto_extraido = await extract_text_from_file(content, file.filename, tipo_archivo, progress_tracker, cancel_check)
        
        # Verificar cancelación después de extracción
        if cancel_check:
            cancel_check()
        
        if not texto_extraido.strip():
            raise ValueError("No se pudo extraer texto del archivo")
        
        # Progreso: Texto extraído (45%)
        if progress_tracker:
            progress_tracker.update_progress(45, f"Texto extraído: {len(texto_extraido)} caracteres")
        
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
                # Progreso: Creando documento en BD (50%)
                if progress_tracker:
                    progress_tracker.update_progress(50, "Registrando documento en base de datos")
                
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
                logger.debug(f"Documento creado en BD con estado 'Pendiente': {documento_creado.CT_Nombre_archivo}")
                
                # 2. Actualizar la ruta en el documento
                await expediente_service.actualizar_ruta_documento(
                    db=db,
                    documento=documento_creado,
                    ruta_archivo=filepath,
                    auto_commit=False
                )
                logger.debug(f"Ruta actualizada en documento")
                
                # 3. COMMIT TEMPRANO - El documento ahora es visible con estado "Pendiente"
                db.commit()
                db.refresh(documento_creado)
                logger.info(f"Documento guardado con estado 'Pendiente' (ID: {documento_creado.CN_Id_documento}) - Iniciando procesamiento...")
                
                # 4. Actualizar metadatos con info de BD
                metadatos.update({
                    "documento_id": documento_creado.CN_Id_documento,  # Usar el nombre correcto del campo
                    "ruta_archivo": filepath
                })
                
                # Progreso: Generando embeddings (60%)
                if progress_tracker:
                    progress_tracker.update_progress(60, "Generando embeddings vectoriales")
                
                # 5. Almacenar en Milvus con IDs reales
                doc_ids, num_chunks = await store_in_vectorstore(
                    texto=texto_extraido, 
                    metadatos=metadatos, 
                    CT_Num_expediente=CT_Num_expediente,
                    id_expediente=expediente.CN_Id_expediente,  # ID real del expediente
                    id_documento=documento_creado.CN_Id_documento  # ID real del documento
                )
                logger.info(f"Almacenado en vectorstore exitosamente: {num_chunks} chunks")
                
                # Registrar en bitácora el almacenamiento vectorial
                if usuario_id:
                    try:
                        from app.services.bitacora.ingesta_audit_service import ingesta_audit_service as bitacora_service
                        await bitacora_service.registrar_almacenamiento_vectorial(
                            db=db,
                            usuario_id=usuario_id,
                            expediente_num=CT_Num_expediente,
                            filename=file.filename,
                            documento_id=documento_creado.CN_Id_documento,
                            num_chunks=num_chunks
                        )
                    except Exception as e:
                        logger.warning(f"Error registrando almacenamiento vectorial en bitácora: {e}")
                
                # Progreso: Finalizando (85%)
                if progress_tracker:
                    progress_tracker.update_progress(85, "Almacenando en vectorstore")
                
                # 6. Actualizar estado a "Procesado" si todo salió bien
                await expediente_service.actualizar_estado_documento(
                    db=db,
                    documento=documento_creado,
                    nuevo_estado="Procesado",
                    auto_commit=False  # No hacer commit aún
                )
                logger.debug(f"Estado actualizado a 'Procesado'")
                
                # 7. Commit final
                db.commit()
                db.refresh(documento_creado)
                logger.info(f"Procesamiento completado exitosamente - Estado: Procesado")
                
            except Exception as e:
                # Manejo de error: actualizar estado según el tipo de excepción
                error_type = type(e).__name__
                
                # Detectar cancelación
                is_cancelled = (
                    error_type in ['Terminated', 'TaskCancelled', 'CancelledError'] or
                    'cancelad' in str(e).lower() or
                    'revoked' in str(e).lower()
                )
                
                if is_cancelled:
                    logger.warning(f"Procesamiento cancelado por el usuario: {str(e)}")
                    nuevo_estado = "Error"  # Usar "Error" para cancelaciones
                    mensaje_log = "cancelado por el usuario"
                    
                    # Actualizar progreso con mensaje de cancelación
                    if progress_tracker:
                        progress_tracker.update_progress(0, "Procesamiento cancelado por el usuario", status="error")
                else:
                    logger.error(f"Error en procesamiento: {str(e)}")
                    nuevo_estado = "Error"
                    mensaje_log = "error en procesamiento"
                    
                    # Actualizar progreso con mensaje de error
                    if progress_tracker:
                        progress_tracker.update_progress(0, f"Error: {str(e)[:100]}", status="error")
                
                try:
                    # El documento ya existe en BD por el commit temprano
                    if documento_creado:
                        # Actualizar estado a "Error"
                        await expediente_service.actualizar_estado_documento(
                            db=db,
                            documento=documento_creado,
                            nuevo_estado=nuevo_estado,
                            auto_commit=True  # Hacer commit del estado
                        )
                        logger.info(f"Estado actualizado a '{nuevo_estado}' para documento {documento_creado.CN_Id_documento} ({mensaje_log})")
                        logger.info(f"Archivo mantenido en disco para auditoría: {filepath}")
                    else:
                        # Caso muy raro: si no hay documento creado, hacer rollback
                        db.rollback()
                        logger.debug("Rollback de BD realizado (sin documento creado)")
                        
                except Exception as cleanup_error:
                    logger.error(f"Error en manejo de estado después de fallo: {str(cleanup_error)}")
                    try:
                        db.rollback()  # Rollback de emergencia
                    except:
                        pass
                
                # Re-lanzar la excepción original
                raise e
        
        else:
            # Sin BD disponible - NO almacenar en Milvus
            logger.warning(f"No se almacena en vectorstore: requiere transacción de BD exitosa")
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
        logger.error(f"Error en procesamiento de archivo: {str(e)}")
        # Re-lanzar la excepción original sin modificar el mensaje
        raise


async def extract_text_from_file(content: bytes, filename: str, content_type: str, progress_tracker: Optional[ProgressTracker] = None, cancel_check: Optional[callable] = None) -> str:
    """
    Extrae texto de diferentes tipos de archivos:
    - Audio (MP3, WAV, OGG, M4A): Transcripción con Whisper
    - Otros formatos (PDF, DOC, DOCX, RTF, TXT, HTML, etc.): Apache Tika Server con Tesseract OCR integrado
    
    Nota: Tika Server tiene Tesseract OCR configurado para extraer texto de PDFs escaneados automáticamente.
    """
    file_extension = Path(filename).suffix.lower()
    
    # Verificar cancelación antes de procesar
    if cancel_check:
        cancel_check()
    
    # Archivos de audio se procesan con Whisper
    if file_extension in ['.mp3', '.wav', '.ogg', '.m4a']:
        return await extract_text_from_audio_whisper(content, filename, cancel_check)
    
    # Los demás formatos con Tika Server (con OCR integrado)
    try:
        import chardet
        
        # Para archivos .txt, detectar codificación y manejar directamente
        if file_extension == '.txt':
            # Detectar codificación automáticamente
            detected = chardet.detect(content)
            encoding = detected.get('encoding') if detected else None
            confidence = detected.get('confidence', 0) if detected else 0
            
            # Si la confianza es alta y tenemos codificación válida, usar la detectada
            if encoding and confidence > 0.7:
                try:
                    texto = content.decode(encoding)
                    logger.info(f"Archivo {filename}: codificación detectada {encoding} (confianza: {confidence:.2f})")
                except UnicodeDecodeError:
                    # Fallback a UTF-8 con manejo de errores
                    texto = content.decode('utf-8', errors='replace')
                    logger.info(f"Archivo {filename}: fallback a UTF-8 con reemplazo de errores")
            else:
                # Intentar UTF-8 primero, luego Latin-1 como fallback
                try:
                    texto = content.decode('utf-8')
                    logger.info(f"Archivo {filename}: usando UTF-8")
                except UnicodeDecodeError:
                    texto = content.decode('latin-1')
                    logger.info(f"Archivo {filename}: usando Latin-1 como fallback")
        else:
            # Para otros formatos, usar Tika Server con OCR integrado
            tika_service = TikaService()
            
            # Tika Server tiene Tesseract OCR configurado automáticamente
            # Para PDFs y documentos escaneados, el OCR se aplica automáticamente
            texto = tika_service.extract_text(
                content=content,
                filename=filename,
                enable_ocr=True  # Habilitar OCR para todos los documentos
            )
        
        if not texto or not texto.strip():
            error_msg = f"No se pudo extraer texto del archivo {filename}"
            if file_extension:
                error_msg += f" (Extensión: {file_extension})"
            error_msg += ". Posibles causas: archivo corrupto, formato no soportado, o archivo protegido con contraseña."
            raise ValueError(error_msg)
        
        # Aplicar limpieza profunda del texto usando el helper
        # (El helper ya incluye detección de problemas de encoding)
        texto_limpio = clean_extracted_text(texto, filename)
        
        # Validar que quedó contenido después de la limpieza
        is_valid, error_msg = validate_cleaned_text(texto_limpio, min_length=10, filename=filename)
        if not is_valid:
            logger.warning(error_msg)
        
        logger.info(f"Texto extraído y limpiado de {filename} ({len(texto_limpio)} caracteres)")
        return texto_limpio
        
    except Exception as e:
        error_detallado = f"Error extrayendo texto de {filename}"
        if file_extension:
            error_detallado += f" (tipo: {file_extension})"
        error_detallado += f": {str(e)}"
        logger.error(error_detallado)
        raise ValueError(error_detallado)

async def extract_text_from_audio_whisper(content: bytes, filename: str, cancel_check: Optional[callable] = None) -> str:
    """
    Transcribe audio MP3 usando faster-whisper optimizado.
    Sistema secuencial inteligente: intenta directo primero, chunks si es necesario.
    """
    try:
        # Verificar cancelación al inicio
        if cancel_check:
            cancel_check()
        
        from ..audio_transcription.whisper_service import audio_processor
        from app.config.audio_config import AUDIO_CONFIG
        
        # Log de configuración
        file_size_mb = len(content) / (1024 * 1024)
        logger.info(f"Procesando audio {filename}: {file_size_mb:.1f} MB")
        logger.debug(f"Configuración: modelo={AUDIO_CONFIG.whisper_model}, device={AUDIO_CONFIG.device}")
        logger.debug(f"faster-whisper: compute_type={AUDIO_CONFIG.compute_type}, workers={AUDIO_CONFIG.num_workers}")
        logger.debug(f"Chunks si archivo >= {AUDIO_CONFIG.enable_chunking_threshold_mb} MB o falla directo")
        logger.debug(f"Procesamiento: SECUENCIAL OPTIMIZADO (sin paralelismo)")
        
        # Verificar cancelación antes de transcribir
        if cancel_check:
            cancel_check()
        
        # Usar el procesador de audio optimizado
        texto = await audio_processor.transcribe_audio_direct(content, filename, cancel_check)
        
        # Verificar cancelación después de transcribir
        if cancel_check:
            cancel_check()
        
        if not texto.strip():
            raise ValueError("No se pudo transcribir el audio")
        
        logger.info(f"Transcripción completada: {len(texto)} caracteres")
        return texto
        
    except ImportError as e:
        logger.error(f"Error de importación en transcripción de audio: {e}")
        if 'faster_whisper' in str(e).lower():
            raise ValueError("faster-whisper no está disponible. Instalar con 'pip install faster-whisper'")
        else:
            raise ValueError(f"Error de dependencia en transcripción de audio: {str(e)}")
    except Exception as e:
        logger.error(f"Error transcribiendo audio {filename}: {str(e)}")
        raise ValueError(f"Error transcribiendo audio {filename}: {str(e)}")
