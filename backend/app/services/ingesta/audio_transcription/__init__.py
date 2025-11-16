"""
Transcripción de audio con faster-whisper.

Módulo especializado para convertir audio a texto con estrategias
modulares y selección automática.

Módulos:
    * whisper_service: Orquestador con selección de estrategia
    * direct_strategy: Transcripción directa (archivos <100 MB)
    * chunking_strategy: Transcripción con chunks (archivos ≥100 MB)
    * audio_utils: Utilidades (duración, splitting, cleanup)

Estrategias:
    DirectTranscriptionStrategy:
        * Archivos pequeños (<100 MB)
        * Una sola llamada a Whisper
        * Más rápido
    
    ChunkingTranscriptionStrategy:
        * Archivos grandes (>=100 MB)
        * División con overlap
        * Más robusto

Características:
    * Lazy loading del modelo Whisper
    * Selección automática de estrategia
    * Fallback si estrategia primaria falla
    * Progress tracking detallado
    * Liberación de memoria automática
    * Idioma español optimizado

Uso:
    >>> from app.services.ingesta.audio_transcription.whisper_service import AudioTranscriptionOrchestrator
    >>> 
    >>> orchestrator = AudioTranscriptionOrchestrator()
    >>> texto = await orchestrator.transcribe(
    ...     audio_path="audiencia.mp3",
    ...     task_id="task_123"
    ... )

Ver también:
    * app.services.ingesta.document_processor: Usa orchestrator
    * app.config.audio_config: Configuración Whisper
"""
