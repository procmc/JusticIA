"""Reloj del sistema: la hora y los plazos pasan por aquí para poder controlarlos en las pruebas.

El código que necesita saber la hora o medir un plazo (el tiempo máximo del envío de correo, las
caducidades de los códigos de recuperación) pide el reloj con `obtener_reloj()` en lugar de llamar
a `datetime`, `time` o `asyncio.wait_for` directamente. En producción es siempre `RelojReal`; las
pruebas lo reemplazan por uno que adelantan a voluntad (`tests/soporte/reloj.py`), así ninguna
espera tiempo real para comprobar un plazo (RA-02.9). No agrega ninguna dependencia.

El reloj se pide en cada uso, no al construir un objeto: los servicios que se crean al importar el
módulo usan así el reloj que la prueba haya instalado.

Ver también: `tests/soporte/reloj.py` (reloj controlable y su fixture).
"""
import asyncio
import time
from datetime import datetime, timezone
from typing import Awaitable, TypeVar

T = TypeVar("T")


class RelojReal:
    """El reloj de producción: hora UTC del sistema, reloj monótono y esperas reales."""

    def ahora(self) -> datetime:
        """La hora actual en UTC, con zona (nunca una fecha sin zona)."""
        return datetime.now(timezone.utc)

    def monotonico(self) -> float:
        """Segundos de un reloj que solo avanza; sirve para medir duraciones, no para fechar."""
        return time.monotonic()

    async def dormir(self, segundos: float) -> None:
        """Espera `segundos` sin bloquear el bucle de eventos."""
        await asyncio.sleep(segundos)

    async def con_limite(self, corrutina: Awaitable[T], segundos: float) -> T:
        """Devuelve el resultado de `corrutina`; si tarda más de `segundos`, la cancela y lanza `TimeoutError`."""
        return await asyncio.wait_for(corrutina, segundos)


# El reloj en uso. Solo lo cambia la fixture de pruebas (con `monkeypatch`, que lo restaura sola);
# el código del sistema lo lee siempre a través de `obtener_reloj()`.
_reloj_en_uso = RelojReal()


def obtener_reloj() -> RelojReal:
    """El reloj que el sistema debe usar ahora: el real, salvo que una prueba haya instalado otro."""
    return _reloj_en_uso
