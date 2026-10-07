"""Plugin de la corrida hija que desactiva la limpieza por prueba (spec 002, RA-02.7; T8).

Se carga con `-p tests.infraestructura.plugin_sin_limpieza` en un proceso hijo de `pytest` (no lo recolecta ninguna
corrida: su nombre no empieza por `test_`). Reemplaza la rutina de limpieza por una que no hace nada, para demostrar
que el cierre de la sesión de la hija DETECTA lo que quedó (filas, puntos, archivos) y falla nombrándolo.
"""
from tests.soporte import datos

datos.limpiar = lambda destino, registro: None
