import os
import uuid
from datetime import datetime
from typing import List
from pathlib import Path
from fastapi import UploadFile, HTTPException
import filetype

from app.schemas.schemas import (
    FileUploadResponse, 
    FileValidationError, 
    FileProcessingStatus
)
from app.config.file_config import ALLOWED_FILE_TYPES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS
from app.vectorstore.milvus_storage import store_in_vectorstore

async def process_uploaded_files(files: List[UploadFile], expediente: str) -> FileProcessingStatus:
    """
    Procesa una lista de archivos subidos para un expediente específico.
    """
    archivos_procesados = []
    archivos_con_error = []
    
    for file in files:
        try:
            # Validar archivo
            validation_error = validate_file(file)
            if validation_error:
                archivos_con_error.append(validation_error)
                continue
            
            # Procesar archivo
            result = await process_single_file(file, expediente)
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

async def process_single_file(file: UploadFile, expediente: str) -> FileUploadResponse:
    """
    Procesa un solo archivo: extrae texto y lo almacena en Milvus.
    """
    file_id = str(uuid.uuid4())
    
    try:
        # Leer contenido del archivo
        content = await file.read()
        
        # Detectar tipo de archivo usando filetype
        detected_type = filetype.guess(content)
        tipo_archivo = detected_type.mime if detected_type else file.content_type
        
        # Extraer texto según el tipo
        texto_extraido = await extract_text_from_file(content, file.filename, tipo_archivo)
        
        if not texto_extraido.strip():
            raise ValueError("No se pudo extraer texto del archivo")
        
        # Preparar metadatos
        metadatos = {
            "file_id": file_id,
            "nombre_archivo": file.filename,
            "tipo_archivo": tipo_archivo,
            "expediente": expediente,
            "fecha_procesamiento": datetime.now().isoformat(),
            "tamaño_archivo": len(content)
        }
        
        # Almacenar en Milvus
        await store_in_vectorstore(texto_extraido, metadatos, expediente)
        
        # Reiniciar posición del archivo para futuras operaciones
        await file.seek(0)
        
        return FileUploadResponse(
            status="success",
            message="Archivo procesado exitosamente",
            file_id=file_id,
            expediente=expediente,
            nombre_archivo=file.filename,
            tipo_archivo=tipo_archivo,
            fecha_procesamiento=datetime.now(),
            texto_extraido_preview=texto_extraido[:200] + "..." if len(texto_extraido) > 200 else texto_extraido,
            metadatos=metadatos
        )
        
    except Exception as e:
        return FileUploadResponse(
            status="error",
            message="Error procesando archivo",
            file_id=file_id,
            expediente=expediente,
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
        
        # Extraer el texto
        texto = parsed.get('content', '')
        
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
    Transcribe audio MP3 usando Whisper.
    El modelo se configura desde la variable de entorno WHISPER_MODEL.
    """
    try:
        import whisper
        import tempfile
        import os
        from app.config.config import WHISPER_MODEL
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Cargar modelo Whisper desde configuración
            model = whisper.load_model(WHISPER_MODEL)
            
            # Transcribir
            result = model.transcribe(temp_file_path)
            
            texto = result["text"].strip()
            
            if not texto:
                raise ValueError("No se pudo transcribir el audio")
            
            return texto
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except ImportError:
        raise ValueError("OpenAI Whisper no está disponible. Instalar con 'pip install openai-whisper'")
    except Exception as e:
        raise ValueError(f"Error transcribiendo audio {filename}: {str(e)}")
