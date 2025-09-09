"""
Servicio simplificado para procesamiento de audio con faster-whisper.
Sistema secuencial optimizado sin paralelismo - máximo rendimiento y confiabilidad.
"""
import os
import tempfile
import asyncio
from typing import List, Optional
import logging

from app.config.audio_config import AUDIO_CONFIG, AudioProcessingConfig

logger = logging.getLogger(__name__)

class AudioChunkProcessor:
    """Procesador de audio secuencial optimizado con faster-whisper."""
    
    def __init__(self, config: Optional[AudioProcessingConfig] = None):
        self.config = config or AUDIO_CONFIG
        self._whisper_model = None
        
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
                
                logger.info("faster-whisper modelo cargado exitosamente")
                
            except Exception as e:
                logger.error(f"Error cargando modelo faster-whisper: {e}")
                raise
        return self._whisper_model
    
    async def transcribe_audio_direct(self, audio_content: bytes, filename: str) -> str:
        """
        Transcripción inteligente de audio completo.
        Intenta procesar completo primero, recurre a chunks si es necesario.
        """
        temp_file_path = None
        
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_content)
                temp_file_path = temp_file.name
            
            file_size_mb = len(audio_content) / (1024 * 1024)
            logger.info(f"Transcribiendo audio {filename} ({file_size_mb:.1f} MB) con faster-whisper")
            
            # Intentar transcripción directa primero
            try:
                model = self._load_faster_whisper_model()
                
                # Ejecutar transcripción en thread separado para no bloquear
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._transcribe_file_sync, 
                    temp_file_path
                )
                
                if not result.strip():
                    raise ValueError("Transcripción directa resultó en texto vacío")
                
                logger.info(f"Transcripción directa exitosa: {len(result)} caracteres")
                return result
                
            except Exception as direct_error:
                logger.warning(f"Transcripción directa falló: {direct_error}")
                
                # Si es un archivo grande o falló por memoria, usar chunks
                if file_size_mb >= self.config.enable_chunking_threshold_mb or "memory" in str(direct_error).lower():
                    logger.info(f"Recurriendo a procesamiento con chunks...")
                    return await self._transcribe_with_chunks(temp_file_path, filename)
                else:
                    # Re-lanzar error si no es un problema de tamaño
                    raise direct_error
                
        except Exception as e:
            logger.error(f"Error transcribiendo audio {filename}: {e}")
            raise ValueError(f"Error transcribiendo audio {filename}: {str(e)}")
        
        finally:
            # Limpieza
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
    
    def _transcribe_file_sync(self, file_path: str) -> str:
        """Función auxiliar síncrona para transcribir un archivo con faster-whisper."""
        model = self._load_faster_whisper_model()
        
        # Transcribir con faster-whisper
        segments, info = model.transcribe(
            file_path, 
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
        
        # Log información adicional
        logger.info(f"Idioma detectado: {info.language} (probabilidad: {info.language_probability:.2f})")
        logger.info(f"Duración: {info.duration:.1f}s")
        
        return full_text
    
    async def _transcribe_with_chunks(self, audio_path: str, filename: str) -> str:
        """Transcribe audio dividido en chunks secuencialmente."""
        chunk_paths = []
        
        try:
            # Obtener duración del audio
            duration = await self._get_audio_duration(audio_path)
            logger.info(f"Duración del audio: {duration/60:.1f} minutos")
            
            # Dividir en chunks
            chunk_paths = await self._split_audio_into_chunks(audio_path)
            
            if not chunk_paths:
                raise ValueError("No se pudieron crear chunks de audio")
            
            logger.info(f"Transcribiendo {len(chunk_paths)} chunks secuencialmente con faster-whisper")
            
            # Transcribir cada chunk secuencialmente
            transcriptions = []
            model = self._load_faster_whisper_model()
            
            for i, chunk_path in enumerate(chunk_paths):
                try:
                    logger.info(f"Transcribiendo chunk {i + 1}/{len(chunk_paths)}")
                    
                    # Transcribir chunk en thread separado
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, 
                        self._transcribe_file_sync, 
                        chunk_path
                    )
                    
                    transcriptions.append(result)
                    
                    # Log de progreso
                    progress = ((i + 1) / len(chunk_paths)) * 100
                    logger.info(f"Progreso: {progress:.1f}% - Chunk {i + 1} completado: {len(result)} caracteres")
                    
                except Exception as e:
                    logger.error(f"Error transcribiendo chunk {i + 1}: {e}")
                    transcriptions.append("")  # Continuar con chunk vacío
            
            # Unir todas las transcripciones
            full_text = " ".join(transcriptions).strip()
            logger.info(f"Transcripción por chunks completada: {len(full_text)} caracteres totales")
            
            if not full_text:
                raise ValueError("No se pudo transcribir ningún chunk del audio")
            
            return full_text
            
        finally:
            # Limpieza de chunks temporales
            await self._cleanup_chunks(chunk_paths)
    
    async def _get_audio_duration(self, audio_path: str) -> float:
        """Obtiene la duración del audio en segundos."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Convertir ms a segundos
        except Exception as e:
            logger.warning(f"No se pudo obtener duración de audio: {e}")
            return 0.0
    
    async def _split_audio_into_chunks(self, audio_path: str) -> List[str]:
        """Divide el audio en chunks y retorna las rutas de los archivos temporales."""
        try:
            from pydub import AudioSegment
            
            # Cargar audio
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            
            # Configuración de chunks
            chunk_duration_ms = self.config.chunk_duration_minutes * 60 * 1000
            overlap_ms = self.config.chunk_overlap_seconds * 1000
            
            chunks_paths = []
            chunk_start = 0
            chunk_index = 0
            
            logger.info(f"Dividiendo audio en chunks de {self.config.chunk_duration_minutes} min con overlap de {self.config.chunk_overlap_seconds}s")
            
            while chunk_start < duration_ms:
                # Calcular fin del chunk
                chunk_end = min(chunk_start + chunk_duration_ms, duration_ms)
                
                # Extraer chunk con overlap
                if chunk_index > 0:
                    # Para chunks posteriores, incluir overlap al inicio
                    chunk_start_with_overlap = max(0, chunk_start - overlap_ms)
                else:
                    chunk_start_with_overlap = chunk_start
                
                chunk = audio[chunk_start_with_overlap:chunk_end]
                
                # Guardar chunk temporal
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'_chunk_{chunk_index}.mp3')
                chunk.export(temp_file.name, format="mp3")
                chunks_paths.append(temp_file.name)
                
                logger.info(f"Chunk {chunk_index + 1}: {chunk_start_with_overlap/1000:.1f}s - {chunk_end/1000:.1f}s")
                
                # Avanzar al siguiente chunk
                chunk_start = chunk_end
                chunk_index += 1
                
                # Limitar número de chunks por seguridad
                if chunk_index >= 50:
                    logger.warning("Límite de 50 chunks alcanzado, truncando audio")
                    break
            
            logger.info(f"Audio dividido en {len(chunks_paths)} chunks")
            return chunks_paths
            
        except Exception as e:
            logger.error(f"Error dividiendo audio: {e}")
            raise ValueError(f"Error en división de audio: {str(e)}")
    
    async def _cleanup_chunks(self, chunk_paths: List[str]):
        """Limpia archivos temporales de chunks."""
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.unlink(chunk_path)
            except Exception as e:
                logger.warning(f"Error limpiando chunk {chunk_path}: {e}")

# Instancia global del procesador
audio_processor = AudioChunkProcessor()
