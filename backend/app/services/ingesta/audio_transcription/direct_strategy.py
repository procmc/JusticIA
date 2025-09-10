"""
Estrategia de procesamiento directo de audio con faster-whisper.
Camino principal optimizado para archivos que pueden procesarse completos.
"""
import asyncio
from typing import Optional
import logging

from app.config.audio_config import AudioProcessingConfig
from ..async_processing.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class DirectTranscriptionStrategy:
    """Estrategia de transcripción directa sin división en chunks."""
    
    def __init__(self, whisper_model, config: AudioProcessingConfig):
        self.whisper_model = whisper_model
        self.config = config
    
    async def transcribe(self, temp_file_path: str, filename: str, 
                        file_size_mb: float, progress_tracker: Optional[ProgressTracker] = None) -> str:
        """
        Ejecuta transcripción directa del archivo completo.
        
        Args:
            temp_file_path: Ruta al archivo temporal
            filename: Nombre original del archivo
            file_size_mb: Tamaño del archivo en MB
            progress_tracker: Tracker para reportar progreso
            
        Returns:
            str: Texto transcrito
            
        Raises:
            ValueError: Si la transcripción falla o resulta vacía
        """
        try:
            logger.info(f"Iniciando transcripción directa de {filename} ({file_size_mb:.1f} MB)")
            
            if progress_tracker:
                progress_tracker.update_progress(20, "Modelo cargado, iniciando transcripción directa")
            
            # Ejecutar transcripción en thread separado para no bloquear
            loop = asyncio.get_event_loop()
            
            if progress_tracker:
                progress_tracker.update_progress(30, "Transcribiendo archivo completo...")
            
            result = await loop.run_in_executor(
                None, 
                self._transcribe_file_sync_with_progress, 
                temp_file_path,
                progress_tracker
            )
            
            if not result.strip():
                raise ValueError("Transcripción directa resultó en texto vacío")
            
            if progress_tracker:
                progress_tracker.update_progress(95, "Transcripción directa completada", 
                                               {"characters_transcribed": len(result),
                                                "strategy": "direct"})
            
            logger.info(f"Transcripción directa exitosa: {len(result)} caracteres")
            return result
            
        except Exception as e:
            error_msg = f"Error en transcripción directa de {filename}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _transcribe_file_sync_with_progress(self, file_path: str, 
                                          progress_tracker: Optional[ProgressTracker] = None) -> str:
        """Función auxiliar síncrona para transcribir un archivo con faster-whisper y progreso granular."""
        
        if progress_tracker:
            progress_tracker.update_progress(35, "Iniciando transcripción con Whisper")  # Transcribir con faster-whisper
        segments, info = self.whisper_model.transcribe(
            file_path, 
            beam_size=5,
            language="es",  # Forzar español para mejor rendimiento
            condition_on_previous_text=False,  # Mejor para archivos completos
            temperature=0.0,  # Determinístico
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6
        )
        
        if progress_tracker:
            progress_tracker.update_progress(60, "Procesando segmentos de audio")
        
        # Unir segmentos en texto completo con progreso más granular
        text_parts = []
        segment_count = 0
        last_progress = 60
        
        # Convertir generador a lista para poder contar total de segmentos
        segments_list = list(segments)
        total_segments = len(segments_list)
        
        if progress_tracker and total_segments > 0:
            progress_tracker.update_progress(65, f"Procesando {total_segments} segmentos detectados",
                                           {"total_segments": total_segments})
        
        for i, segment in enumerate(segments_list):
            text_parts.append(segment.text.strip())
            segment_count += 1
            
            # Calcular progreso granular (65% a 90% durante procesamiento de segmentos)
            if total_segments > 0:
                segment_progress = 65 + int((i + 1) / total_segments * 25)  # 65% a 90%
                
                # Reportar progreso cada 5% o cada 10 segmentos, lo que ocurra primero
                if progress_tracker and (segment_progress > last_progress + 4 or segment_count % 10 == 0):
                    last_progress = segment_progress
                    progress_tracker.update_progress(
                        segment_progress,
                        f"Segmento {segment_count}/{total_segments} - {segment.text[:50]}...",
                        {
                            "segments_processed": segment_count,
                            "total_segments": total_segments,
                            "current_segment_start": f"{segment.start:.1f}s",
                            "current_segment_end": f"{segment.end:.1f}s",
                            "characters_so_far": len(" ".join(text_parts))
                        }
                    )
        
        full_text = " ".join(text_parts).strip()
        
        # Log información adicional
        logger.info(f"Idioma detectado: {info.language} (probabilidad: {info.language_probability:.2f})")
        logger.info(f"Duración: {info.duration:.1f}s")
        logger.info(f"Segmentos procesados: {segment_count}")
        
        if progress_tracker:
            progress_tracker.update_progress(90, f"Transcripción completada: {segment_count} segmentos procesados",
                                           {"segments_count": segment_count, 
                                            "duration": info.duration,
                                            "language": info.language,
                                            "language_probability": info.language_probability,
                                            "total_characters": len(full_text)})
        
        return full_text
    
    def can_handle(self, file_size_mb: float, error_context: Optional[str] = None) -> bool:
        """
        Determina si esta estrategia puede manejar el archivo.
        
        Args:
            file_size_mb: Tamaño del archivo en MB
            error_context: Contexto de error previo (opcional)
            
        Returns:
            bool: True si puede manejar el archivo
        """
        # Puede manejar archivos menores al umbral
        # O archivos que no fallaron por memoria
        if file_size_mb < self.config.enable_chunking_threshold_mb:
            return True
        
        # Si hay contexto de error, verificar si no es problema de memoria
        if error_context and "memory" not in error_context.lower():
            return True
            
        return False
    
    def get_strategy_name(self) -> str:
        """Retorna el nombre de la estrategia."""
        return "direct_transcription"
