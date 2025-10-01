from pathlib import Path
import os
import shutil


def ensure_model_available(model_id: str, dest_root: str = "models") -> bool:
    """Verifica si model_id está disponible en dest_root; si no, intenta descargarlo usando huggingface_hub.

    Retorna True si el modelo ya estaba o se descargó correctamente, False si no se pudo asegurar.
    """
    if not model_id:
        return False

    sanitized = model_id.replace('/', '__')
    final_dir = Path(dest_root) / sanitized

    # Si ya hay pesos comunes, consideramos el modelo presente
    if final_dir.exists() and (any(final_dir.glob('*.safetensors')) or any(final_dir.glob('*.bin'))):
        print(f"Modelo '{model_id}' disponible")
        return True
    
    print(f"Descargando modelo: {model_id} (~2.5GB)")

    try:
        # import aquí para no requerir la dependencia si no se usa
        from huggingface_hub import snapshot_download
        import sys
    except Exception as e:
        print(f"huggingface_hub no disponible: {e}")
        return False

    try:
        # Forzar que tqdm muestre el progreso en stdout/stderr
        sys.stdout.flush()
        sys.stderr.flush()
        
        # snapshot_download mostrará automáticamente el progreso con tqdm
        # (resume_download ya no es necesario, ahora siempre reintenta automáticamente)
        snapshot_path = snapshot_download(
            repo_id=model_id
        )
        snapshot_path = Path(snapshot_path)
        
        # Copiar a directorio final
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(snapshot_path, final_dir)
        
        print(f"Modelo '{model_id}' descargado")
        return True
    except Exception as e:
        print(f"Error descarga: {e}")
        return False
