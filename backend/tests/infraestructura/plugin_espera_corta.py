"""Plugin de la corrida hija que acorta la espera de los servicios (spec 002, RA-02.4; T5).

Se carga con `-p tests.infraestructura.plugin_espera_corta` en un proceso hijo de `pytest` (no lo
recolecta ninguna corrida: su nombre no empieza por `test_`). Cambia solo cuánto espera `esperar_servicio`
(3 segundos en vez de 60) para que la prueba de «Qdrant no responde» no dure un minuto. Los 60 segundos
reales los comprueban las unitarias con un reloj simulado; aquí se comprueba lo que pasa DESPUÉS de
rendirse: el aborto nombra el servicio y la base de pruebas igual se elimina.
"""
from tests.soporte import entorno

SEGUNDOS_DE_ESPERA = 3
INTERVALO = 0.5

_esperar_servicio_original = entorno.esperar_servicio


def _esperar_servicio_corto(servicio, intentar, **espera):
    espera.update(segundos=SEGUNDOS_DE_ESPERA, intervalo=INTERVALO)
    return _esperar_servicio_original(servicio, intentar, **espera)


entorno.esperar_servicio = _esperar_servicio_corto
