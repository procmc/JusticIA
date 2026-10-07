"""Plugin de la corrida hija que comprueba el aborto por nombre inválido (spec 002, RA-02.3 b; plan, decisión 14).

Se carga con `-p tests.infraestructura.plugin_nombre_invalido` en un proceso hijo de `pytest` (no lo
recolecta ninguna corrida: su nombre no empieza por `test_`). Hace dos cosas ANTES de que el
`conftest.py` de la raíz fije el entorno de la suite:

1. cambia el nombre de base que la suite escribiría en su configuración por el de la base de desarrollo
   (la protección sigue comparando con el nombre de pruebas verdadero, así que debe abortar);
2. apunta el servidor de SQL Server a una dirección que no responde, para que, si la protección no
   abortara antes de conectarse, la salida fuera la de «no responde» y no la del aborto por nombre.
"""
import os

from tests.soporte import configuracion

NOMBRE_DE_DESARROLLO_FALSO = "base_de_desarrollo_falsa"
DIRECCION_QUE_NO_RESPONDE = "10.255.255.1"  # no enrutable: una conexión se quedaría esperando

configuracion.NOMBRE_PRUEBAS = NOMBRE_DE_DESARROLLO_FALSO
os.environ["SQL_SERVER_HOST"] = DIRECCION_QUE_NO_RESPONDE
