"""
Estrategia de procesamiento con chunks para archivos grandes.
Camino de fallback para cuando la transcripción directa no es viable.
"""
import asyncio
from typing import List, Optional
import logging

from app.config.audio_config import AudioProcessingConfig
from ..async_processing.progress_tracker import ProgressTracker
from .audio_utils import AudioUtils

logger = logging.getLogger(__name__)

class ChunkingTranscriptionStrategy:
    """Estrategia de transcripción con división en chunks para archivos grandes."""
    
    def __init__(self, whisper_model, config: AudioProcessingConfig):
        self.whisper_model = whisper_model
        self.config = config
        self.audio_utils = AudioUtils()
    
    async def transcribe(self, temp_file_path: str, filename: str, 
                        file_size_mb: float, progress_tracker: Optional[ProgressTracker] = None) -> str:
        """
        Ejecuta transcripción con división en chunks.
        
        Args:
            temp_file_path: Ruta al archivo temporal
            filename: Nombre original del archivo
            file_size_mb: Tamaño del archivo en MB
            progress_tracker: Tracker para reportar progreso
            
        Returns:
            str: Texto transcrito completo
            
        Raises:
            ValueError: Si la transcripción falla
        """
        chunk_paths = []
        
        try:
            logger.info(f"Iniciando transcripción con chunks de {filename} ({file_size_mb:.1f} MB)")
            
            if progress_tracker:
                progress_tracker.update_progress(30, "Analizando duración del audio")
            
            # Obtener duración del audio
            duration = await self.audio_utils.get_audio_duration(temp_file_path)
            logger.info(f"Duración del audio: {duration/60:.1f} minutos")
            
            if progress_tracker:
                progress_tracker.update_progress(35, "Dividiendo audio en chunks")
            
            # Dividir en chunks
            chunk_paths = await self.audio_utils.split_audio_into_chunks(
                temp_file_path, 
                self.config.chunk_duration_minutes,
                self.config.chunk_overlap_seconds
            )
            
            if not chunk_paths:
                raise ValueError("No se pudieron crear chunks de audio")
            
            logger.info(f"Transcribiendo {len(chunk_paths)} chunks secuencialmente con faster-whisper")
            
            if progress_tracker:
                progress_tracker.update_progress(40, f"Audio dividido en {len(chunk_paths)} chunks", 
                                               {"total_chunks": len(chunk_paths), 
                                                "duration_minutes": duration/60,
                                                "strategy": "chunking"})
            
            # Transcribir chunks
            transcriptions = await self._transcribe_chunks(chunk_paths, progress_tracker)
            
            if progress_tracker:
                progress_tracker.update_progress(95, "Uniendo transcripciones de todos los chunks")
            
            # Unir todas las transcripciones
            full_text = " ".join(transcriptions).strip()
            logger.info(f"Transcripción por chunks completada: {len(full_text)} caracteres totales")
            
            if not full_text:
                error_msg = "No se pudo transcribir ningún chunk del audio"
                raise ValueError(error_msg)
            
            if progress_tracker:
                progress_tracker.metadata.update({
                    "total_characters": len(full_text), 
                    "chunks_processed": len(chunk_paths),
                    "strategy": "chunking"
                })
            
            return full_text
            
        except Exception as e:
            error_msg = f"Error en transcripción por chunks de {filename}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        finally:
            # Limpieza de chunks temporales
            await self.audio_utils.cleanup_chunks(chunk_paths)
    
    async def _transcribe_chunks(self, chunk_paths: List[str], 
                               progress_tracker: Optional[ProgressTracker] = None) -> List[str]:
        """
        Transcribe todos los chunks secuencialmente.
        
        Args:
            chunk_paths: Lista de rutas a los archivos de chunks
            progress_tracker: Tracker para reportar progreso
            
        Returns:
            List[str]: Lista de transcripciones de cada chunk
        """
        transcriptions = []
        
        # Progreso base: 40% (preparación) + 50% (transcripción) + 10% (finalización)
        chunk_progress_start = 40
        chunk_progress_range = 50
        
        for i, chunk_path in enumerate(chunk_paths):
            try:
                # Calcular progreso del chunk actual
                chunk_progress = chunk_progress_start + (i * chunk_progress_range // len(chunk_paths))
                
                if progress_tracker:
                    progress_tracker.update_progress(
                        chunk_progress,
                        f"Transcribiendo chunk {i + 1}/{len(chunk_paths)}",
                        {"current_chunk": i + 1, "total_chunks": len(chunk_paths)}
                    )
                
                logger.info(f"Transcribiendo chunk {i + 1}/{len(chunk_paths)}")
                
                # Transcribir chunk en thread separado
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._transcribe_single_chunk, 
                    chunk_path
                )
                
                transcriptions.append(result)
                
                # Actualizar progreso después de cada chunk
                chunk_complete_progress = chunk_progress_start + ((i + 1) * chunk_progress_range // len(chunk_paths))
                
                if progress_tracker:
                    progress_tracker.update_progress(
                        chunk_complete_progress,
                        f"Chunk {i + 1}/{len(chunk_paths)} completado: {len(result)} caracteres",
                        {
                            "chunks_completed": i + 1,
                            "chunk_characters": len(result),
                            "total_chunks": len(chunk_paths)
                        }
                    )
                
                # Log de progreso
                progress_percent = ((i + 1) / len(chunk_paths)) * 100
                logger.info(f"Progreso chunks: {progress_percent:.1f}% - Chunk {i + 1} completado: {len(result)} caracteres")
                
            except Exception as e:
                logger.error(f"Error transcribiendo chunk {i + 1}: {e}")
                if progress_tracker:
                    progress_tracker.update_progress(
                        chunk_progress,
                        f"Error en chunk {i + 1}: {str(e)[:50]}...",
                        {"chunk_error": i + 1, "error": str(e)}
                    )
                transcriptions.append("")  # Continuar con chunk vacío
        
        return transcriptions
    
    def _transcribe_single_chunk(self, chunk_path: str) -> str:
        """Transcribe un chunk individual de forma síncrona."""
        try:
            # Transcribir con faster-whisper
            segments, info = self.whisper_model.transcribe(
                chunk_path, 
                beam_size=5,
                language="es",  # Forzar español para mejor rendimiento
                condition_on_previous_text=False,  # Mejor para chunks independientes
                temperature=0.0,  # Determinístico
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            # Unir segmentos en texto completo
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            full_text = " ".join(text_parts).strip()
            
            # Log información adicional del chunk
            logger.debug(f"Chunk transcrito - Idioma: {info.language}, Duración: {info.duration:.1f}s")
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error transcribiendo chunk individual: {e}")
            return ""  # Retornar texto vacío en caso de error
    
    def can_handle(self, file_size_mb: float, error_context: Optional[str] = None) -> bool:
        """
        Determina si esta estrategia puede manejar el archivo.
        
        Args:
            file_size_mb: Tamaño del archivo en MB
            error_context: Contexto de error previo (opcional)
            
        Returns:
            bool: True si puede manejar el archivo
        """
        # Puede manejar archivos grandes o que fallaron por memoria
        if file_size_mb >= self.config.enable_chunking_threshold_mb:
            return True
        
        # Si hay contexto de error de memoria, también puede manejar
        if error_context and "memory" in error_context.lower():
            return True
            
        return False
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia."""
        return "chunking_transcription"
    
    def get_expected_chunks(self, duration_seconds: float) -> int:
        """Calcula el número esperado de chunks basado en la duración."""
        chunk_duration_seconds = self.config.chunk_duration_minutes * 60
        return max(1, int(duration_seconds / chunk_duration_seconds) + 1)
