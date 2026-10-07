"""Pruebas de T5 (spec 002, RA-02.2, RA-02.3 y RA-02.4): la colección de Qdrant de pruebas.

Usan el Qdrant real del entorno, pero solo la colección `servia_pruebas` que la propia suite creó al
empezar la integración (fixture `entorno_integracion`) y eliminará al terminar. Los módulos del sistema
se importan dentro de cada prueba (regla del plan: ningún archivo de pruebas importa `app` al cargarse).
"""
import asyncio
import os

from tests.soporte import entorno
from tests.soporte.nombres import NOMBRE_PRUEBAS


def _informacion_de_la_coleccion():
    """Lo que Qdrant dice de la colección de pruebas (consulta de solo lectura)."""
    cliente = entorno.cliente_qdrant()
    try:
        return cliente.get_collection(NOMBRE_PRUEBAS)
    finally:
        cliente.close()


def test_la_coleccion_de_pruebas_existe_con_la_dimension_y_la_distancia_del_sistema():
    """RA-02.4: durante la corrida de integración la colección existe, con `DIM` dimensiones y distancia coseno."""
    from qdrant_client.models import Distance

    informacion = _informacion_de_la_coleccion()
    vectores = informacion.config.params.vectors

    assert vectores.size == int(os.environ["DIM"]) == 1024
    assert vectores.distance == Distance.COSINE


def test_la_coleccion_de_pruebas_empieza_vacia():
    """RA-02.4: es de uso exclusivo de la suite; sin pruebas que guarden puntos, no tiene ninguno."""
    assert _informacion_de_la_coleccion().points_count == 0


def test_el_nombre_efectivo_de_la_coleccion_que_usa_el_sistema_es_el_de_pruebas():
    """RA-02.2, RA-02.3: lo que importó el sistema (valor efectivo) es la colección de pruebas, no la de desarrollo."""
    from app.config.config import QDRANT_COLLECTION_NAME
    from app.vectorstore import qdrant_backend

    assert QDRANT_COLLECTION_NAME == NOMBRE_PRUEBAS == "servia_pruebas"
    assert qdrant_backend.QDRANT_COLLECTION_NAME == NOMBRE_PRUEBAS


def test_el_vectorstore_del_sistema_habla_con_la_coleccion_de_pruebas():
    """RA-02.2: el código del sistema (sin simulados) llega a la colección `servia_pruebas` y la ve vacía."""
    from app.vectorstore import get_vectorstore_backend

    estadisticas = asyncio.run(get_vectorstore_backend().get_stats())

    assert estadisticas["collection_name"] == "servia_pruebas"
    assert estadisticas["stats"]["points_count"] == 0
