"""
Utilidades compartidas para procesamiento de audio.
Funciones auxiliares para manejo de archivos, duración y división de audio.
"""
import os
import tempfile
import asyncio
from typing import List
import logging

logger = logging.getLogger(__name__)

class AudioUtils:
    """Utilidades auxiliares para manejo de archivos de audio."""
    
    async def get_audio_duration(self, audio_path: str) -> float:
        """Obtiene la duración del audio en segundos."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio) / 1000.0  # Convertir ms a segundos
        except Exception as e:
            logger.warning(f"No se pudo obtener duración de audio: {e}")
            return 0.0
    
    async def split_audio_into_chunks(self, audio_path: str, chunk_duration_minutes: int, 
                                     chunk_overlap_seconds: int) -> List[str]:
        """Divide el audio en chunks y retorna las rutas de los archivos temporales."""
        try:
            from pydub import AudioSegment
            
            # Cargar audio
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)
            
            # Configuración de chunks
            chunk_duration_ms = chunk_duration_minutes * 60 * 1000
            overlap_ms = chunk_overlap_seconds * 1000
            
            chunks_paths = []
            chunk_start = 0
            chunk_index = 0
            
            logger.info(f"Dividiendo audio en chunks de {chunk_duration_minutes} min con overlap de {chunk_overlap_seconds}s")
            
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
    
    async def cleanup_chunks(self, chunk_paths: List[str]):
        """Limpia archivos temporales de chunks."""
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.unlink(chunk_path)
            except Exception as e:
                logger.warning(f"Error limpiando chunk {chunk_path}: {e}")
    
    def create_temp_file(self, content: bytes, suffix: str = '.mp3') -> str:
        """Crea un archivo temporal con el contenido dado."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            return temp_file.name
    
    def cleanup_temp_file(self, file_path: str):
        """Limpia un archivo temporal específico."""
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Error limpiando archivo temporal {file_path}: {e}")
    
    def get_file_size_mb(self, content: bytes) -> float:
        """Calcula el tamaño del contenido en MB."""
        return len(content) / (1024 * 1024)
