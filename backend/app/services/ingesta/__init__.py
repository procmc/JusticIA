"""
Módulo de ingesta de archivos y transcripción de audio.
Centraliza todo el procesamiento de documentos y conversión de audio a texto.

Estructura:
- audio_transcription/    # Transcripción de audio con Whisper
- file_management/        # Procesamiento y almacenamiento de documentos  
- async_processing/       # Tareas en segundo plano

Uso recomendado:
- from app.services.ingesta.audio_transcription.whisper_service import audio_processor
- from app.services.ingesta.file_management.document_processor import process_uploaded_files
- from app.services.ingesta.async_processing.background_tasks import procesar_archivo_individual_en_background
"""

__all__ = [
    # Los módulos están disponibles como submódulos con nombres descriptivos
    # audio_transcription, file_management, async_processing
]
