"""Pruebas de T5 (spec 004a): la carpeta de documentos no es pública y los avatares siguen funcionando.

Cubren RNF-07.22 (los documentos cargados no se obtienen por la dirección pública `/uploads/<tema>/<nombre>`, ni sin
sesión ni con ella) y RF-04.20 (el avatar se entrega con `GET` y `HEAD`, sin sesión y con `?v=`, desde la ubicación de
avatares realmente configurada; un nombre de avatar no válido da 404).

Todo ocurre en la carpeta temporal desviada (`carpeta_archivos`): nunca se toca el `uploads/` real. Los nombres llevan
el prefijo `PRUEBA`.
"""
import pytest

CONTENIDO_DOCUMENTO = b"PRUEBA contenido de un documento que no debe ser publico"
CONTENIDO_AVATAR = b"\x89PNG\r\n\x1a\nPRUEBA avatar inventado"
CONTENIDO_TESTIGO = b"PRUEBA testigo fuera de la carpeta de avatares"
TEMA = "PRUEBA-TEMA-T5-0001"
DOCUMENTO = "PRUEBA_documento.txt"
AVATAR = "PRUEBA_avatar-1.png"


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


@pytest.fixture
def avatares(carpeta_archivos):
    """La carpeta de avatares realmente configurada en el servicio (desviada a la temporal por la fixture)."""
    from app.services.avatar_service import avatar_service

    return avatar_service.upload_dir


def test_documento_no_se_obtiene_por_la_direccion_publica(cliente_api, sesion, carpeta_archivos):
    """RNF-07.22 (b): `/uploads/<tema>/<nombre>` da 404 sin contenido, con y sin token."""
    carpeta = carpeta_archivos / "uploads" / TEMA
    carpeta.mkdir(parents=True)
    (carpeta / DOCUMENTO).write_bytes(CONTENIDO_DOCUMENTO)

    for ruta in (f"/uploads/{TEMA}/{DOCUMENTO}", f"/uploads/{TEMA}/", "/uploads/", "/uploads"):
        for cabeceras in ({}, sesion):
            respuesta = cliente_api.get(ruta, headers=cabeceras, follow_redirects=False)
            assert respuesta.status_code == 404, (ruta, respuesta.status_code)
            assert CONTENIDO_DOCUMENTO not in respuesta.content, ruta


def test_avatar_se_entrega_con_get_y_head(cliente_api, avatares):
    """RF-04.20: sin sesión, `GET` y `HEAD` entregan el avatar de la ubicación configurada; `?v=` se ignora."""
    (avatares / AVATAR).write_bytes(CONTENIDO_AVATAR)

    for sufijo in ("", "?v=1760000000000"):
        ruta = f"/uploads/profiles/{AVATAR}{sufijo}"
        obtenido = cliente_api.get(ruta)
        assert obtenido.status_code == 200, ruta
        assert obtenido.content == CONTENIDO_AVATAR
        assert obtenido.headers["content-type"] == "image/png"

        cabecera = cliente_api.head(ruta)
        assert cabecera.status_code == 200, ruta
        assert cabecera.content == b""
        assert cabecera.headers["content-type"] == "image/png"


def test_avatar_no_se_reutiliza_entre_peticiones_con_y_sin_origen(cliente_api, avatares):
    """RF-04.20 (corrección 1, H2 de T6): el avatar lleva `Vary: Origin` con `GET` y `HEAD`.

    El navegador guarda la respuesta del `<img>` (sin `Origin`, sin `Access-Control-Allow-Origin`) y, sin `Vary`, la
    reutilizaba para el `fetch` CORS de la interfaz, que fallaba por CORS. Con `Origin` permitido, además, responde con
    `Access-Control-Allow-Origin`.
    """
    (avatares / AVATAR).write_bytes(CONTENIDO_AVATAR)
    ruta = f"/uploads/profiles/{AVATAR}"

    for metodo in (cliente_api.get, cliente_api.head):
        sin_origen = metodo(ruta)
        assert sin_origen.status_code == 200
        assert "origin" in sin_origen.headers.get("vary", "").lower(), metodo.__name__

        con_origen = metodo(ruta, headers={"Origin": "http://localhost:3000"})
        assert con_origen.status_code == 200
        assert "access-control-allow-origin" in con_origen.headers, metodo.__name__
        assert "origin" in con_origen.headers.get("vary", "").lower(), metodo.__name__


@pytest.mark.parametrize("nombre", [
    "PRUEBA_avatar.txt",            # extensión no permitida
    "PRUEBA_avatar",                # sin extensión
    ".png",                         # sin nombre
    "PRUEBA avatar.png",            # espacio
    "PRUEBA.avatar.png",            # punto en el nombre
    f"{'a' * 41}.png",              # más de 40 caracteres
    "..%2FPRUEBA_testigo.png",      # recorrido codificado
    "%2e%2e%2fPRUEBA_testigo.png",
    "..%5CPRUEBA_testigo.png",
    "PRUEBA_inexistente.png",       # válido pero sin archivo
    "PRUEBA_carpeta.png",           # una carpeta con nombre válido
    "PRUEBA_enlace.png",            # un enlace que sale de la carpeta
])
def test_nombre_de_avatar_no_valido_da_404(cliente_api, avatares, carpeta_archivos, nombre):
    """RF-04.20: nombre no válido, inexistente, carpeta o enlace que sale: 404 con `GET` y `HEAD`, sin entregar nada."""
    testigo = carpeta_archivos / "PRUEBA_testigo.png"
    testigo.write_bytes(CONTENIDO_TESTIGO)
    (avatares / "PRUEBA_carpeta.png").mkdir()
    (avatares / "PRUEBA_avatar.txt").write_bytes(CONTENIDO_AVATAR)
    try:
        (avatares / "PRUEBA_enlace.png").symlink_to(testigo)
    except OSError:
        pytest.skip("El sistema no permite crear enlaces simbólicos.")

    ruta = f"/uploads/profiles/{nombre}"
    for metodo in (cliente_api.get, cliente_api.head):
        respuesta = metodo(ruta)
        assert respuesta.status_code == 404, (nombre, respuesta.status_code)
        assert CONTENIDO_TESTIGO not in respuesta.content
        assert CONTENIDO_AVATAR not in respuesta.content
