"""Pruebas de T2 (spec 004, RA-02.12): el inventario clasifica todas las rutas registradas.

Unitarias: solo comparan las rutas que la aplicación registra con la tabla de `tests/soporte/inventario_rutas.py`; no
llaman a ninguna ruta ni usan servicios reales. Importar `main` es seguro aquí (lo hace también la prueba de RNF-07.22):
no ejecuta el arranque, que es lo que cargaría los embeddings. Los mensajes de error nombran la ruta que sobra o falta,
porque ese es el requisito (la evidencia y la memoria del proyecto, en cambio, no las listan).
"""
import contextlib
import re
from pathlib import Path

import pytest
from fastapi import FastAPI

from tests.soporte import inventario_rutas as inventario

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def app_real():
    """La aplicación real, importada desde la raíz del backend (`main.py` monta la carpeta relativa `uploads`)."""
    with contextlib.chdir(RAIZ_BACKEND):
        import main
    return main.app


def _copia_con_ruta_nueva(app_real, metodo: str, plantilla: str) -> FastAPI:
    """Una copia de la aplicación (mismas rutas) con una ruta más, registrada solo dentro de la prueba."""
    copia = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    copia.router.routes.extend(app_real.router.routes)
    copia.add_api_route(plantilla, lambda: None, methods=[metodo])
    return copia


@pytest.mark.requisito("RA-02.12")
def test_tabla_igual_a_rutas_registradas(app_real):
    """RA-02.12: ninguna ruta registrada queda sin clasificar y ninguna clasificada ha dejado de existir."""
    registradas = inventario.rutas_registradas(app_real)
    clasificadas = set(inventario.CLASIFICACION)

    sin_clasificar = sorted(registradas - clasificadas)
    inexistentes = sorted(clasificadas - registradas)

    assert not sin_clasificar, f"Rutas registradas sin clasificar: {sin_clasificar}"
    assert not inexistentes, f"Rutas clasificadas que ya no existen: {inexistentes}"
    inventario.exigir_tabla_completa(app_real)  # la misma comprobación, por la función que usarán las demás tareas


@pytest.mark.requisito("RA-02.12")
def test_ruta_sin_clasificar_se_nombra(app_real):
    """RA-02.12: con una ruta de ejemplo agregada a una copia de la aplicación, la comprobación falla y la nombra."""
    copia = _copia_con_ruta_nueva(app_real, "GET", "/PRUEBA-ruta-nueva/{identificador}")

    with pytest.raises(AssertionError) as error:
        inventario.exigir_tabla_completa(copia)

    mensaje = str(error.value)
    assert "/PRUEBA-ruta-nueva/{identificador}" in mensaje
    assert "sin clasificar" in mensaje


@pytest.mark.requisito("RA-02.12")
def test_clasificada_que_ya_no_existe_se_nombra(app_real):
    """RA-02.12: si la tabla clasifica una ruta que la aplicación no tiene, la comprobación falla y la nombra."""
    clasificacion = dict(inventario.CLASIFICACION)
    clasificacion[("GET", "/PRUEBA-ruta-retirada")] = next(iter(clasificacion.values()))

    with pytest.raises(AssertionError) as error:
        inventario.exigir_tabla_completa(app_real, clasificacion)

    mensaje = str(error.value)
    assert "/PRUEBA-ruta-retirada" in mensaje
    assert "ya no existe" in mensaje


@pytest.mark.requisito("RA-02.12")
def test_mismo_metodo_distinto_cuenta_como_ruta_distinta(app_real):
    """RA-02.12: la clave es (método, plantilla): un método nuevo en una plantilla conocida también falta en la tabla."""
    metodo, plantilla = next(c for c in inventario.CLASIFICACION if c[0] == "GET")
    otro = "PUT" if metodo != "PUT" else "POST"
    copia = _copia_con_ruta_nueva(app_real, otro, plantilla)

    with pytest.raises(AssertionError) as error:
        inventario.exigir_tabla_completa(copia)

    assert otro in str(error.value) and plantilla in str(error.value)


@pytest.mark.requisito("RNF-07.5")
def test_avatares_get_y_head_son_publica_deliberada():
    """RF-04.20, RNF-07.22: GET y HEAD de la dirección de avatares son la excepción documentada a RNF-07.5."""
    for metodo in ("GET", "HEAD"):
        entrada = inventario.CLASIFICACION[(metodo, "/uploads/profiles/{nombre}")]
        assert entrada.clase == inventario.PUBLICA_DELIBERADA
        assert entrada.grupo == "avatares"
        assert entrada.estado_actual is None


@pytest.mark.requisito("RNF-07.5")
def test_publicas_y_documentacion_segun_la_spec():
    """Spec 004 (clasificación): inicio de sesión, recuperación y la raíz son públicas; la documentación es protegida."""
    clasificacion = inventario.CLASIFICACION
    for clave in (
        ("POST", "/auth/login"), ("POST", "/auth/solicitar-recuperacion"), ("POST", "/auth/verificar-codigo"),
        ("POST", "/auth/cambiar-contrasenna-recuperacion"), ("GET", "/"),
    ):
        assert clasificacion[clave].clase == inventario.PUBLICA, clave
    for clave in (("GET", "/docs"), ("GET", "/redoc"), ("GET", "/openapi.json"), ("GET", "/docs/oauth2-redirect")):
        assert clasificacion[clave].clase == inventario.PROTEGIDA, clave
        assert clasificacion[clave].estado_actual == inventario.ETIQUETA_AUTENTICACION, clave


def test_la_tabla_es_coherente_consigo_misma():
    """Cada entrada tiene una clase conocida, un id neutro único (sin rutas) y un ejemplo; las etiquetas no nombran rutas."""
    ids = set()
    for (metodo, plantilla), entrada in inventario.CLASIFICACION.items():
        assert entrada.clase in inventario.CLASES, (metodo, plantilla)
        assert re.fullmatch(r"[a-z]+-\d+", entrada.id), entrada.id
        assert entrada.id not in ids, f"Id repetido: {entrada.id}"
        ids.add(entrada.id)
        assert isinstance(entrada.ejemplo, dict)
        assert entrada.flujo_critico in (True, False)
        if entrada.estado_actual is not None:
            assert "/" not in entrada.estado_actual, "La etiqueta de un xfail nunca lleva la ruta"
        # Cada parámetro de la plantilla tiene su valor de ejemplo.
        for nombre in re.findall(r"{(\w+)}", plantilla):
            assert nombre in entrada.ejemplo.get("parametros", {}), (metodo, plantilla, nombre)


def test_ruta_con_parametros_se_arma_con_el_ejemplo():
    """`ruta_de_ejemplo` sustituye los parámetros de la plantilla por los valores de `PRUEBA` del ejemplo."""
    ruta = inventario.ruta_de_ejemplo(("GET", "/notebooks/{notebook_id}/documentos"))
    assert "{" not in ruta and ruta.startswith("/notebooks/") and ruta.endswith("/documentos")
