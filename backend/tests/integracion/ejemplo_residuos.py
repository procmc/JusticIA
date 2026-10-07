"""Prueba de ejemplo para las corridas hijas de `tests/infraestructura/test_residuos.py` (spec 002, RA-02.7).

NO es una prueba de la suite: su nombre no empieza por `test_`, así que ninguna corrida normal la recolecta; solo
corre cuando una prueba de infraestructura la pasa como argumento a un `pytest` hijo. Crea una fila, un punto y un
archivo, y termina sin limpiar nada: de eso se encarga la limpieza automática de cada prueba, y si no lo hiciera,
el cierre de la sesión de la hija la encontraría y fallaría.
"""
from tests.soporte import datos, entorno, simulados
from tests.soporte.nombres import PREFIJO_DATOS


def test_crea_una_fila_un_punto_y_un_archivo_y_termina(registro_de_datos):
    cliente = entorno.cliente_qdrant()
    try:
        datos.crear_usuario(datos.ROL_ADMINISTRADOR, registro_de_datos)
        datos.crear_punto(cliente, registro_de_datos)
        registro_de_datos.crear_archivo(
            simulados.carpeta_temporal_de_la_sesion(), f"{PREFIJO_DATOS}_archivo_del_ejemplo.txt", b"texto inventado"
        )
    finally:
        cliente.close()
