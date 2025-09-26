from pathlib import Path
import os
import shutil


def ensure_model_available(model_id: str, dest_root: str = "models") -> bool:
    """Verifica si model_id está disponible en dest_root; si no, intenta descargarlo usando huggingface_hub.

    Retorna True si el modelo ya estaba o se descargó correctamente, False si no se pudo asegurar.
    Esta función es intencionalmente pequeña y sin logging complejo para mantenerla simple.
    """
    if not model_id:
        return False

    sanitized = model_id.replace('/', '__')
    final_dir = Path(dest_root) / sanitized

    # Si ya hay pesos comunes, consideramos el modelo presente
    if final_dir.exists() and (any(final_dir.glob('*.safetensors')) or any(final_dir.glob('*.bin'))):
        return True

    try:
        # import aquí para no requerir la dependencia si no se usa
        from huggingface_hub import snapshot_download
    except Exception:
        # huggingface_hub no está disponible
        return False

    try:
        # No pasamos token para modelos públicos (token no es necesario)
        # Intentar reanudar descargas parciales si existen
        snapshot_path = snapshot_download(repo_id=model_id, resume_download=True)
        snapshot_path = Path(snapshot_path)
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(snapshot_path, final_dir)
        return True
    except Exception:
        return False
