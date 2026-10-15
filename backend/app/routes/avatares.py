"""
Entrega pública de avatares de perfil: `GET`/`HEAD /uploads/profiles/{nombre}` (RF-04.20, RNF-07.22).

EXCEPCIÓN deliberada a dos reglas de `.claude/rules/api-conventions.md`:
    * «Todo endpoint exige rol»: esta ruta no pide sesión. La interfaz pide la imagen con un `fetch` y como `<img>`,
      que no llevan el token; exigirlo cambiaría el frontend y se decidirá en la spec de autenticación.
    * `prefix="/<modulo>"`: se registra con `prefix="/uploads/profiles"` para conservar la dirección que ya usan la
      interfaz y los datos guardados (`CT_Avatar_ruta`).

Solo entrega avatares (nombre `<id>.<extensión de imagen>` dentro de la carpeta de avatares); la carpeta de
documentos ya no se publica. El parámetro `?v=` de la interfaz (para saltar la caché) se ignora.

Ver también:
    * app.services.avatar_service: `obtener_ubicacion_avatar_publico`
    * app.routes.usuarios: subida y cambio de avatar (con sesión)
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.avatar_service import avatar_service

router = APIRouter()


@router.api_route("/{nombre}", methods=["GET", "HEAD"], include_in_schema=False)
def entregar_avatar(nombre: str) -> FileResponse:
    """Entrega el avatar o responde 404 «Archivo no encontrado» si el nombre no es válido o no existe."""
    ubicacion = avatar_service.obtener_ubicacion_avatar_publico(nombre)
    if ubicacion is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    # `Vary: Origin`: la respuesta del `<img>` (sin `Origin`, sin `Access-Control-Allow-Origin`) no debe reutilizarse
    # en el `fetch` CORS de la interfaz, que fallaba por CORS con el avatar en la caché del navegador.
    return FileResponse(ubicacion, headers={"Vary": "Origin"})
