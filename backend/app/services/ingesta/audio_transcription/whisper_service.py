"""
Servicio orquestador para procesamiento de audio con faster-whisper.
Sistema modular con estrategias separadas para procesamiento directo y chunks.
"""
import os
from typing import Optional
import logging

from app.config.audio_config import AUDIO_CONFIG, AudioProcessingConfig
from ..async_processing.progress_tracker import ProgressTracker
from .audio_utils import AudioUtils
from .direct_strategy import DirectTranscriptionStrategy
from .chunking_strategy import ChunkingTranscriptionStrategy

logger = logging.getLogger(__name__)

class AudioTranscriptionOrchestrator:
    """
    Orquestador principal para transcripción de audio.
    Selecciona automáticamente la mejor estrategia (directa o chunks) según el contexto.
    """
    
    def __init__(self, config: Optional[AudioProcessingConfig] = None):
        self.config = config or AUDIO_CONFIG
        self._whisper_model = None
        self.audio_utils = AudioUtils()
        
        # Estrategias de procesamiento (se inicializan cuando se carga el modelo)
        self.direct_strategy = None
        self.chunking_strategy = None
        
    def _load_faster_whisper_model(self):
        """Carga el modelo faster-whisper (lazy loading) con optimizaciones."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                
                logger.info(f"Cargando faster-whisper modelo '{self.config.whisper_model}' en {self.config.device}")
                logger.info(f"Configuración: compute_type={self.config.compute_type}, workers={self.config.num_workers}")
                
                # Configurar modelo con optimizaciones
                self._whisper_model = WhisperModel(
                    model_size_or_path=self.config.whisper_model,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                    num_workers=self.config.num_workers,
                    download_root=None,  # Usar caché por defecto
                    local_files_only=False
                )
                
                # Inicializar estrategias con el modelo cargado
                self.direct_strategy = DirectTranscriptionStrategy(self._whisper_model, self.config)
                self.chunking_strategy = ChunkingTranscriptionStrategy(self._whisper_model, self.config)
                
                logger.info("faster-whisper modelo y estrategias cargadas exitosamente")
                
            except Exception as e:
                logger.error(f"Error cargando modelo faster-whisper: {e}")
                raise
        return self._whisper_model
    
    async def transcribe_audio_direct(self, audio_content: bytes, filename: str, 
                                     cancel_check: Optional[callable] = None,
                                     progress_tracker: Optional[ProgressTracker] = None) -> str:
        """
        Transcripción inteligente de audio usando estrategias modulares.
        Selecciona automáticamente la mejor estrategia: directa primero, chunks como fallback.
        """
        temp_file_path = None
        
        try:
            # Verificar cancelación al inicio
            if cancel_check:
                cancel_check()
            
            # Paso 1: Preparación inicial (0-5%)
            if progress_tracker:
                progress_tracker.update_progress(2, f"Iniciando procesamiento de {filename}")
            
            # Crear archivo temporal
            temp_file_path = self.audio_utils.create_temp_file(audio_content)
            file_size_mb = self.audio_utils.get_file_size_mb(audio_content)
            
            # Verificar cancelación
            if cancel_check:
                cancel_check()
            
            if progress_tracker:
                progress_tracker.update_progress(5, f"Archivo temporal creado ({file_size_mb:.1f} MB)", 
                                               {"file_size_mb": file_size_mb})

            logger.info(f"Transcribiendo audio {filename} ({file_size_mb:.1f} MB) con faster-whisper")
            
            # Paso 2: Análisis del archivo (5-15%)
            if progress_tracker:
                progress_tracker.update_progress(8, "Analizando archivo de audio")
            
            # Verificar cancelación
            if cancel_check:
                cancel_check()
            
            # Obtener duración del audio para mejor estimación de progreso
            try:
                duration = await self.audio_utils.get_audio_duration(temp_file_path)
                if progress_tracker:
                    progress_tracker.update_progress(12, f"Audio analizado: {duration/60:.1f} minutos", 
                                                   {"duration_seconds": duration})
            except Exception as e:
                logger.warning(f"No se pudo obtener duración del audio: {e}")
                if progress_tracker:
                    progress_tracker.update_progress(12, "Continuando sin análisis de duración")

            # Paso 3: Carga del modelo (12-20%)
            if progress_tracker:
                progress_tracker.update_progress(15, "Cargando modelo faster-whisper")
            
            model = self._load_faster_whisper_model()
            
            if progress_tracker:
                progress_tracker.update_progress(20, "Modelo cargado, seleccionando estrategia")
            
            # Paso 4: Selección y ejecución de estrategia (20-95%)
            strategy = self._select_strategy(file_size_mb)
            logger.info(f"Estrategia seleccionada: {strategy.get_strategy_name()} (umbral: {self.config.enable_chunking_threshold_mb} MB)")
            
            if progress_tracker:
                progress_tracker.update_progress(25, f"Ejecutando estrategia: {strategy.get_strategy_name()}", 
                                               {"strategy": strategy.get_strategy_name()})
            
            try:
                # Intentar estrategia principal (generalmente directa)
                result = await strategy.transcribe(temp_file_path, filename, file_size_mb, progress_tracker)
                
                # Paso 5: Finalización (95-100%)
                if progress_tracker:
                    progress_tracker.mark_completed(f"Audio transcrito exitosamente: {len(result)} caracteres usando {strategy.get_strategy_name()}")
                
                return result
                
            except Exception as strategy_error:
                logger.warning(f"Estrategia {strategy.get_strategy_name()} falló: {strategy_error}")
                
                # Intentar estrategia de fallback
                fallback_strategy = self._get_fallback_strategy(file_size_mb, str(strategy_error))
                
                if fallback_strategy and fallback_strategy != strategy:
                    if progress_tracker:
                        progress_tracker.update_progress(25, f"Recurriendo a estrategia de fallback: {fallback_strategy.get_strategy_name()}")
                    
                    logger.info(f"Recurriendo a estrategia de fallback: {fallback_strategy.get_strategy_name()}")
                    result = await fallback_strategy.transcribe(temp_file_path, filename, file_size_mb, progress_tracker)
                    
                    if progress_tracker:
                        progress_tracker.mark_completed(f"Audio transcrito con fallback: {len(result)} caracteres usando {fallback_strategy.get_strategy_name()}")
                    
                    return result
                else:
                    # No hay estrategia de fallback disponible
                    if progress_tracker:
                        progress_tracker.mark_failed(f"Error en transcripción: {str(strategy_error)}", str(strategy_error))
                    raise strategy_error
                
        except Exception as e:
            error_msg = f"Error transcribiendo audio {filename}: {str(e)}"
            logger.error(error_msg)
            if progress_tracker:
                progress_tracker.mark_failed(error_msg, str(e))
            raise ValueError(error_msg)
        
        finally:
            # Limpieza
            if temp_file_path:
                self.audio_utils.cleanup_temp_file(temp_file_path)
    
    def _select_strategy(self, file_size_mb: float):
        """Selecciona la estrategia principal basada en el tamaño del archivo."""
        # Asegurar que las estrategias estén inicializadas
        if not self.direct_strategy or not self.chunking_strategy:
            self._load_faster_whisper_model()
        
        # Verificación adicional de seguridad
        if not self.direct_strategy or not self.chunking_strategy:
            raise RuntimeError("Error inicializando estrategias de transcripción")
        
        # Preferir estrategia directa para archivos menores al umbral
        if self.direct_strategy.can_handle(file_size_mb):
            return self.direct_strategy
        else:
            return self.chunking_strategy
    
    def _get_fallback_strategy(self, file_size_mb: float, error_context: str):
        """Obtiene la estrategia de fallback basada en el contexto de error."""
        # Asegurar que las estrategias estén inicializadas
        if not self.direct_strategy or not self.chunking_strategy:
            self._load_faster_whisper_model()
        
        # Verificación adicional de seguridad
        if not self.direct_strategy or not self.chunking_strategy:
            return None
        
        # Si la estrategia directa falló, intentar chunks
        if self.chunking_strategy.can_handle(file_size_mb, error_context):
            return self.chunking_strategy
        
        # Si chunks falló, intentar directa (por si era un error temporal)
        if self.direct_strategy.can_handle(file_size_mb, error_context):
            return self.direct_strategy
        
        return None
    
    def get_strategy_info(self, file_size_mb: float) -> dict:
        """Obtiene información sobre qué estrategia se usaría para un archivo."""
        try:
            primary_strategy = self._select_strategy(file_size_mb)
            
            return {
                "file_size_mb": file_size_mb,
                "threshold_mb": self.config.enable_chunking_threshold_mb,
                "primary_strategy": primary_strategy.get_strategy_name(),
                "will_use_chunking": isinstance(primary_strategy, ChunkingTranscriptionStrategy),
                "fallback_available": True  # Siempre hay fallback en el diseño actual
            }
        except Exception as e:
            logger.error(f"Error obteniendo información de estrategia: {e}")
            return {
                "file_size_mb": file_size_mb,
                "threshold_mb": self.config.enable_chunking_threshold_mb,
                "primary_strategy": "unknown",
                "will_use_chunking": file_size_mb >= self.config.enable_chunking_threshold_mb,
                "fallback_available": False,
                "error": str(e)
            }


# Instancia global del orquestador
audio_processor = AudioTranscriptionOrchestrator()
