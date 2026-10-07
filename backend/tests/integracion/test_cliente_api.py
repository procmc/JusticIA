"""Pruebas de T5 (spec 002, RA-02.4): el cliente de la API de la integración.

El cliente se crea sin ejecutar el arranque de `main.py`, que cargaría el modelo de embeddings (plan, §2).
"""


def test_el_cliente_de_la_api_responde_sin_ejecutar_el_arranque(cliente_api):
    """RA-02.4: la API responde por el cliente de prueba y el arranque (que carga los embeddings) no se ejecutó."""
    respuesta = cliente_api.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json()["message"] == "ServIA API está funcionando"
    assert cliente_api.portal is None  # solo `with TestClient(...)` abre el portal que ejecuta el arranque
