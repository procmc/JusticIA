# Integración del HTR al backend — pasos para aplicar a mano

> Estos cambios tocan `backend/**` y `docker-compose.yml`, que se editan a
> mano por decisión de trabajo. Acá están los fragmentos exactos.
>
> Corresponde a la **segunda mitad del Ciclo 1** (28/09–01/10):
> *"Integrar el modelo elegido al flujo y documentar"*.

---

## Paso 1 · Mover el cliente

```
htr/integracion_backend/htr_service.py
        ->  backend/app/services/ingesta/htr_service.py
```

Queda al lado de `tika_service.py`, que es su modelo.

## Paso 2 · `backend/app/config/config.py`

Agregar junto a `TIKA_SERVER_URL` (línea 19):

```python
HTR_SERVER_URL = os.getenv("HTR_SERVER_URL", "http://servidor-htr:9100")
HTR_TIMEOUT = int(os.getenv("HTR_TIMEOUT", "300"))
```

## Paso 3 · `backend/app/config/file_config.py` línea 25

Habilitar imágenes. **Antes:**

```python
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.rtf', '.txt', '.html', '.htm', '.xhtml', '.mp3', '.wav', '.ogg', '.m4a']
```

**Después:**

```python
ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.rtf', '.txt', '.html', '.htm', '.xhtml', '.mp3', '.wav', '.ogg', '.m4a', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']
```

## Paso 4 · `backend/app/services/ingesta/file_management/document_processor.py`

En `extract_text_from_file()` (línea ~594), **después** de la rama de
audio y **antes** de la de Tika:

```python
    # Imágenes: reconocimiento de manuscrito (HTR) en su propio servicio
    if file_extension in ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']:
        from app.services.ingesta.htr_service import htr_service
        return htr_service.extract_text(content, filename)
```

> **Ojo con el orden.** Tiene que ir *antes* de la rama de Tika: Tika
> también acepta imágenes y las procesaría con Tesseract, que **no lee
> manuscrito**. Si queda después, nunca se ejecuta.

## Paso 5 · `docker-compose.yml` (el principal)

Agregar el servicio, y `depends_on` en `backend` y `celery-worker`:

```yaml
  servidor-htr:
    build: ./htr
    command: uvicorn servidor_htr:app --host 0.0.0.0 --port 9100
    ports:
      - "9100:9100"
    volumes:
      - ./htr:/htr
      - htr_hf_cache:/cache/huggingface
    environment:
      - HF_HOME=/cache/huggingface
      - PYTHONUNBUFFERED=1
      - HTR_MODELO=qantev/trocr-large-spanish
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Y en `volumes:` del final:

```yaml
  htr_hf_cache:
```

## Paso 6 · `backend/.env`

```
HTR_SERVER_URL=http://servidor-htr:9100
HTR_TIMEOUT=300
```

---

## ⚠️ Antes de aplicar el paso 5: el problema de la VRAM

Medición real con `nvidia-smi`, servidor HTR cargado con
`trocr-large-spanish`:

| | VRAM |
|---|---|
| Base del sistema (sin nada cargado) | ~0.35 GB |
| Total con el servidor HTR arriba | **2.80 GB** |
| → neto del HTR | **~2.45 GB** |
| Ollama con `llama3.1:8b` | ~5.5 GB |
| **Suma** | **~7.95 GB de 8 GB** |

Queda **al filo**: entra sobre el papel, sin margen para ningún picoded
de inferencia. Cualquier imagen grande o un contexto largo en el chat
puede producir un *out of memory*.

Y el riesgo concreto: si Ollama es el que pierde, el chat vuelve a caer a
CPU — los ~5 minutos por respuesta que se corrigieron el 10/09.

> Nota: el contador interno de torch reporta 3.43 GB porque cuenta
> memoria *reservada* además de la asignada. El valor que importa para
> esta cuenta es el de `nvidia-smi`.

Opciones, en orden de preferencia:

| Opción | Cómo | Costo |
|---|---|---|
| **Modelo base en vez de large** | `HTR_MODELO=qantev/trocr-base-spanish` (~1.5 GB) | Peor CER; medir primero |
| **HTR en CPU** | Quitar la reserva de GPU del servicio | ~10-20× más lento, pero la ingesta es asíncrona (Celery) y puede tolerarlo |
| **Descarga por inactividad** | Liberar el modelo tras N minutos sin uso | Hay que programarlo |
| **Levantar el HTR solo cuando se necesita** | `docker compose up servidor-htr` a demanda | Manual, sirve para demos |

**Para las demos**, lo más simple y seguro: dejar el HTR **apagado** por
defecto y levantarlo únicamente cuando se vaya a mostrar la ingesta de
manuscrito.

Esta restricción hay que resolverla **antes** de dejar el HTR en el
`docker-compose.yml` principal con `restart: unless-stopped`.

## Prueba de la integración

```bash
# 1. Servidor arriba y modelo cargado
curl http://localhost:9100/salud

# 2. Reconocimiento directo
curl -X POST --data-binary @foto.jpg http://localhost:9100/htr

# 3. Por el flujo real: subir una imagen desde el frontend y revisar
#    que el texto llegue a Qdrant y aparezca en el chat RAG.
```
