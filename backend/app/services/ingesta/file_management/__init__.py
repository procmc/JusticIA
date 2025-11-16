"""
Gestión y procesamiento de documentos.

Módulo para ingesta, validación y almacenamiento transaccional de archivos.

Módulos:
    * document_processor: Procesador principal con transacciones atómicas
    * text_cleaner: Limpieza y normalización de texto extraído

Características:
    * Validación de archivos (extensión, tamaño, tipo MIME)
    * Extracción de texto (Tika para PDF/docs, Whisper para audio)
    * Limpieza de texto (encoding, espacios, artefactos OCR)
    * Transacciones atómicas (BD + vectorstore)
    * Progress tracking y cancelación

Uso:
    >>> from app.services.ingesta.file_management.document_processor import process_uploaded_files
    >>> from app.services.ingesta.file_management.text_cleaner import clean_extracted_text

Ver también:
    * app.services.ingesta.tika_service: Extracción PDF/docs
    * app.services.ingesta.audio_transcription: Transcripción audio
"""
