"""
"""
Módulo de ingesta de archivos y transcripción de audio.

Centraliza todo el procesamiento de documentos (PDF, DOCX, audio) desde
carga hasta almacenamiento en vectorstore.

Arquitectura:
    * Extracción: Tika (PDF/docs) + Whisper (audio)
    * Limpieza: Normalización Unicode + corrección encoding
    * Almacenamiento: BD (PostgreSQL) + vectorstore (Milvus)
    * Async: Celery workers con progress tracking
    * Transaccional: Commit temprano para visibilidad

Estructura:
    audio_transcription/
        * whisper_service.py: Orquestador de transcripción
        * direct_strategy.py: Estrategia directa (<100 MB)
        * chunking_strategy.py: Estrategia chunks (≥100 MB)
        * audio_utils.py: Utilidades (duración, splitting)
    
    file_management/
        * document_processor.py: Procesador principal
        * text_cleaner.py: Limpieza de texto
    
    async_processing/
        * celery_tasks.py: Tarea procesar_archivo_celery
        * progress_tracker.py: Sistema tracking Redis
    
    tika_service.py: Cliente HTTP para Tika Server

Flujo completo:
    1. Usuario sube archivos (FastAPI endpoint)
    2. Validación: extensión, tamaño, tipo MIME
    3. Creación documento en BD (estado "Pendiente")
    4. Commit temprano (visibilidad inmediata)
    5. Tarea Celery asíncrona:
        a. Extracción texto (Tika/Whisper)
        b. Limpieza texto (normalización)
        c. Almacenamiento vectorstore (chunks + embeddings)
        d. Actualización estado "Procesado"/"Error"
    6. Progress tracking en Redis (compartido)
    7. Bitácora completa de operaciones

Uso recomendado:
    >>> from app.services.ingesta.audio_transcription.whisper_service import AudioTranscriptionOrchestrator
    >>> from app.services.ingesta.file_management.document_processor import process_uploaded_files
    >>> from app.services.ingesta.async_processing.celery_tasks import procesar_archivo_celery
    >>> from app.services.ingesta.tika_service import tika_service
    >>> 
    >>> # Procesamiento síncrono (desarrollo)
    >>> status = await process_uploaded_files(
    ...     files=archivos,
    ...     CT_Num_expediente="00-000001-0001-PE",
    ...     db=db_session,
    ...     usuario_id="user_123"
    ... )
    >>> 
    >>> # Procesamiento asíncrono (producción)
    >>> result = procesar_archivo_celery.apply_async(
    ...     args=[expediente, archivos_data, usuario_id],
    ...     task_id=f"task_{expediente}_{timestamp}"
    ... )

Note:
    * Módulo crítico: conecta input con almacenamiento
    * Transacciones atómicas BD + vectorstore
    * Progress tracking compartido procesos
    * Idempotencia en Celery (evita reintentos)
    * Bitácora completa para auditoría

Ver también:
    * app.vectorstore.milvus_storage: Almacenamiento vectorial
    * app.embeddings.embeddings: Generación de vectores
    * app.routes.expedientes: Endpoints de subida
    * app.celery_app: Configuración Celery

Authors:
    JusticIA Team

Version:
    2.0.0 - Arquitectura modular con estrategias
"""

__all__ = [
    # Los módulos están disponibles como submódulos con nombres descriptivos
    # audio_transcription, file_management, async_processing
]
