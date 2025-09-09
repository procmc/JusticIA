"""
Servicio para procesamiento de audio con chunks adaptativos.
Maneja tanto procesamiento secuencial como paralelo según recursos disponibles.
"""
import os
import tempfile
import asyncio
import concurrent.futures
import functools
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

from app.config.audio_config import AUDIO_CONFIG, AudioProcessingConfig

logger = logging.getLogger(__name__)

class AudioChunkProcessor:
    """Procesador de audio con chunks adaptativos."""
    
    def __init__(self, config: Optional[AudioProcessingConfig] = None):
        self.config = config or AUDIO_CONFIG
        self._whisper_model = None
        
    async def should_use_chunking(self, file_size_bytes: int) -> bool:
        """Determina si se debe usar chunking basado en el tamaño del archivo."""
        file_size_mb = file_size_bytes / (1024 * 1024)
        return file_size_mb >= self.config.enable_chunking_threshold_mb
    
    async def get_audio_duration(self, audio_path: str) -> float:
        """Obtiene la duración del audio en segundos."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Convertir ms a segundos
        except Exception as e:
            logger.warning(f"No se pudo obtener duración de audio: {e}")
            return 0.0
    
    async def split_audio_into_chunks(self, audio_path: str) -> List[str]:
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
                
                logger.info(f"Chunk {chunk_index + 1}: {chunk_start_with_overlap/1000:.1f}s - {chunk_end/1000:.1f}s → {temp_file.name}")
                
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
    
    def _load_whisper_model(self):
        """Carga el modelo Whisper (lazy loading)."""
        if self._whisper_model is None:
            try:
                import whisper
                logger.info(f"Cargando modelo Whisper '{self.config.whisper_model}' en {self.config.device}")
                self._whisper_model = whisper.load_model(self.config.whisper_model, device=self.config.device)
            except Exception as e:
                logger.error(f"Error cargando modelo Whisper: {e}")
                raise
        return self._whisper_model
    
    def _transcribe_chunk_wrapper(self, args: Tuple[str, int]) -> Tuple[int, str]:
        """Wrapper para transcripción de chunk que acepta argumentos como tupla."""
        chunk_path, chunk_index = args
        return self._transcribe_single_chunk(chunk_path, chunk_index)
    
    def _transcribe_single_chunk(self, chunk_path: str, chunk_index: int) -> Tuple[int, str]:
        """Transcribe un chunk individual (función síncrona para threading)."""
        try:
            model = self._load_whisper_model()
            
            logger.info(f"Transcribiendo chunk {chunk_index + 1}")
            result = model.transcribe(chunk_path, verbose=False)
            
            if not isinstance(result, dict) or "text" not in result:
                raise ValueError(f"Respuesta inesperada de Whisper para chunk {chunk_index}")
                
            # Whisper puede devolver text como string o lista
            raw_text = result["text"]
            if isinstance(raw_text, list):
                text = " ".join(str(item) for item in raw_text).strip()
            else:
                text = str(raw_text).strip()
                
            logger.info(f"Chunk {chunk_index + 1} transcrito: {len(text)} caracteres")
            
            return chunk_index, text
            
        except Exception as e:
            logger.error(f"Error transcribiendo chunk {chunk_index + 1}: {e}")
            raise
    
    async def transcribe_chunks_parallel(self, chunk_paths: List[str]) -> str:
        """Transcribe chunks en paralelo usando ThreadPoolExecutor."""
        if not chunk_paths:
            return ""
        
        max_workers = min(self.config.max_parallel_chunks, len(chunk_paths))
        logger.info(f"Transcribiendo {len(chunk_paths)} chunks en paralelo (max_workers={max_workers})")
        
        # Usar ThreadPoolExecutor para paralelización
        loop = asyncio.get_event_loop()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Crear tareas para todos los chunks usando wrapper
            tasks = [
                loop.run_in_executor(
                    executor, 
                    self._transcribe_chunk_wrapper,
                    (chunk_path, i)
                )
                for i, chunk_path in enumerate(chunk_paths)
            ]
            
            # Ejecutar todas las tareas y recoger resultados
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        transcriptions = [""] * len(chunk_paths)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error en transcripción paralela: {result}")
                raise result
            elif isinstance(result, tuple) and len(result) == 2:
                chunk_index, text = result
                transcriptions[chunk_index] = text
            else:
                logger.error(f"Resultado inesperado: {type(result)}")
                raise ValueError(f"Resultado inesperado en transcripción: {type(result)}")
        
        # Unir transcripciones
        full_text = " ".join(transcriptions).strip()
        logger.info(f"Transcripción paralela completada: {len(full_text)} caracteres totales")
        
        return full_text
    
    async def transcribe_chunks_sequential(self, chunk_paths: List[str]) -> str:
        """Transcribe chunks secuencialmente."""
        if not chunk_paths:
            return ""
        
        logger.info(f"Transcribiendo {len(chunk_paths)} chunks secuencialmente")
        
        transcriptions = []
        
        for i, chunk_path in enumerate(chunk_paths):
            try:
                # Ejecutar transcripción síncrona en thread separado
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._transcribe_chunk_wrapper,
                    (chunk_path, i)
                )
                _, text = result
                transcriptions.append(text)
                
                # Log de progreso
                progress = ((i + 1) / len(chunk_paths)) * 100
                logger.info(f"Progreso: {progress:.1f}% ({i + 1}/{len(chunk_paths)})")
                
            except Exception as e:
                logger.error(f"Error transcribiendo chunk {i + 1}: {e}")
                # Continuar con el siguiente chunk
                transcriptions.append("")
        
        # Unir transcripciones
        full_text = " ".join(transcriptions).strip()
        logger.info(f"Transcripción secuencial completada: {len(full_text)} caracteres totales")
        
        return full_text
    
    async def cleanup_chunks(self, chunk_paths: List[str]):
        """Limpia archivos temporales de chunks."""
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.unlink(chunk_path)
            except Exception as e:
                logger.warning(f"Error limpiando chunk {chunk_path}: {e}")
    
    async def transcribe_audio_with_chunks(self, audio_content: bytes, filename: str) -> str:
        """
        Método principal para transcribir audio con chunks adaptativos.
        
        Args:
            audio_content: Contenido del archivo de audio
            filename: Nombre del archivo para logging
            
        Returns:
            str: Texto transcrito completo
        """
        temp_audio_path = None
        chunk_paths = []
        
        try:
            # Verificar si se debe usar chunking
            should_chunk = await self.should_use_chunking(len(audio_content))
            
            if not should_chunk:
                logger.info(f"Archivo {filename} < {self.config.enable_chunking_threshold_mb}MB, procesamiento directo")
                return await self._transcribe_direct(audio_content, filename)
            
            logger.info(f"Archivo {filename} >= {self.config.enable_chunking_threshold_mb}MB, usando chunks")
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_content)
                temp_audio_path = temp_file.name
            
            # Obtener duración para logging
            duration = await self.get_audio_duration(temp_audio_path)
            logger.info(f"Duración del audio: {duration/60:.1f} minutos")
            
            # Dividir en chunks
            chunk_paths = await self.split_audio_into_chunks(temp_audio_path)
            
            if not chunk_paths:
                raise ValueError("No se pudieron crear chunks de audio")
            
            # Transcribir chunks (paralelo o secuencial)
            if self.config.enable_parallel_processing and len(chunk_paths) > 1:
                full_text = await self.transcribe_chunks_parallel(chunk_paths)
            else:
                full_text = await self.transcribe_chunks_sequential(chunk_paths)
            
            if not full_text.strip():
                raise ValueError("No se pudo transcribir el audio")
            
            return full_text
            
        except Exception as e:
            logger.error(f"Error en transcripción con chunks: {e}")
            raise ValueError(f"Error transcribiendo audio {filename}: {str(e)}")
        
        finally:
            # Limpieza
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
            
            if chunk_paths:
                await self.cleanup_chunks(chunk_paths)
    
    async def _transcribe_direct(self, audio_content: bytes, filename: str) -> str:
        """Transcripción directa sin chunks (para archivos pequeños)."""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(audio_content)
                temp_file_path = temp_file.name
            
            try:
                model = self._load_whisper_model()
                result = model.transcribe(temp_file_path, verbose=False)
                
                if not isinstance(result, dict) or "text" not in result:
                    raise ValueError("Respuesta inesperada de Whisper")
                    
                # Whisper puede devolver text como string o lista                def split_audio_into_chunks():
                    # Ejemplo: Audio de 30 minutos, chunks de 10 min
                    # Chunk 1: 0:00 - 10:00
                    # Chunk 2: 9:30 - 19:30  (overlap de 30s)
                    # Chunk 3: 19:00 - 30:00 (overlap de 30s)
                raw_text = result["text"]
                if isinstance(raw_text, list):
                    text = " ".join(str(item) for item in raw_text).strip()
                else:
                    text = str(raw_text).strip()
                    
                if not text:
                    raise ValueError("No se pudo transcribir el audio")
                
                return text
                
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise ValueError(f"Error en transcripción directa de {filename}: {str(e)}")

# Instancia global del procesador
audio_processor = AudioChunkProcessor()
