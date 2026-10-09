"""Reloj controlable de la suite (spec 003a, RA-02.9).

El sistema obtiene la hora y mide sus plazos con `app.utils.reloj.obtener_reloj()`. Aquí está el reloj
que lo reemplaza en las pruebas: el tiempo es VIRTUAL, solo avanza cuando la prueba llama a `avanzar()`,
así que comprobar un plazo de 15 s o de 15 minutos no cuesta tiempo real.

- `RelojControlable` tiene las mismas cuatro operaciones que `RelojReal` (`ahora`, `monotonico`, `dormir`,
  `con_limite`) más `avanzar()` y `esperas_pendientes`. Es asíncrono: solo sirve dentro de un bucle de
  eventos que la propia prueba controla (`asyncio.run`). Una petición hecha con `TestClient` corre en
  otro hilo y otro bucle, y la prueba no puede adelantar un reloj mientras ella está en curso.
- `reloj_controlable` (fixture) lo instala como el reloj del sistema con `monkeypatch`, que lo restaura
  al terminar la prueba: no queda estado compartido entre pruebas y el valor por omisión es el real.

Este módulo es también un plugin de pytest (lo declara el `conftest.py` raíz) y no importa `app` al
cargarse: lo hace dentro de las funciones, como el resto de `tests/soporte/`.
"""
import asyncio
import contextlib
import itertools
from datetime import datetime, timedelta, timezone
from typing import Awaitable, List, TypeVar

import pytest

T = TypeVar("T")

# Valores iniciales del tiempo virtual: una fecha fija en UTC y un reloj monótono que no parte de cero
# (un `monotonico()` en cero podría confundirse con «sin dato»).
_HORA_INICIAL = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_MONOTONICO_INICIAL = 1000.0

# Cuántas veces cede el control al bucle tras liberar una espera: lo que necesita la corrutina liberada
# (y las tareas que dependen de ella) para avanzar hasta su siguiente espera. Es cuestión de iteraciones
# del bucle, no de tiempo.
_CESIONES = 25

# Margen para comparar plazos sumados con decimales (4,9 + 0,1 puede no ser exactamente 5,0).
_TOLERANCIA = 1e-9


class _Espera:
    """Una espera pendiente: se libera cuando el tiempo virtual llega a `plazo`."""

    __slots__ = ("plazo", "orden", "futuro")

    def __init__(self, plazo: float, orden: int, futuro: "asyncio.Future[None]"):
        self.plazo = plazo
        self.orden = orden  # desempata los plazos iguales: gana la que se registró primero
        self.futuro = futuro


class RelojControlable:
    """Reloj de tiempo virtual: `dormir` y `con_limite` solo avanzan cuando la prueba llama a `avanzar`."""

    def __init__(self) -> None:
        self._monotonico = _MONOTONICO_INICIAL
        self._esperas: List[_Espera] = []
        self._contador = itertools.count()

    # --- Lo mismo que RelojReal ---

    def ahora(self) -> datetime:
        """La hora virtual en UTC, con zona."""
        return _HORA_INICIAL + timedelta(seconds=self._monotonico - _MONOTONICO_INICIAL)

    def monotonico(self) -> float:
        """El reloj monótono virtual."""
        return self._monotonico

    async def dormir(self, segundos: float) -> None:
        """Espera `segundos` de tiempo virtual: no termina hasta que la prueba los avance."""
        if segundos <= 0:
            await asyncio.sleep(0)
            return
        espera = self._registrar(segundos)
        try:
            await espera.futuro
        finally:
            self._quitar(espera)

    async def con_limite(self, corrutina: Awaitable[T], segundos: float) -> T:
        """Devuelve el resultado de `corrutina`; si el plazo virtual se cumple antes, la cancela y lanza `TimeoutError`."""
        tarea = asyncio.ensure_future(corrutina)
        espera = self._registrar(segundos)
        try:
            await asyncio.wait({tarea, espera.futuro}, return_when=asyncio.FIRST_COMPLETED)
            if tarea.done():
                return tarea.result()
            await self._cancelar(tarea)
            raise TimeoutError()
        except asyncio.CancelledError:
            # Cancelaron a quien espera: la tarea interna también se cancela y se espera su cancelación.
            await self._cancelar(tarea)
            raise
        finally:
            self._quitar(espera)

    # --- Lo propio del reloj controlable ---

    @property
    def esperas_pendientes(self) -> int:
        """Cuántas esperas (`dormir` o plazos de `con_limite`) siguen registradas."""
        return len(self._esperas)

    async def avanzar(self, segundos: float) -> None:
        """Adelanta el tiempo virtual `segundos`, liberando en orden de plazo las esperas que se cumplen.

        Antes de cada paso cede el control al bucle para que las tareas recién creadas registren su
        espera y, después de liberar una, para que la corrutina registre la siguiente. Así cuatro esperas
        de 5 s seguidas piden 20 s: no se cumplen todas de una vez.
        """
        if segundos < 0:
            raise ValueError("El reloj controlable solo avanza (segundos >= 0).")
        objetivo = self._monotonico + segundos
        await self._ceder()
        while True:
            vencidas = [e for e in self._esperas if not e.futuro.done() and e.plazo <= objetivo + _TOLERANCIA]
            if not vencidas:
                break
            espera = min(vencidas, key=lambda e: (e.plazo, e.orden))
            self._monotonico = max(self._monotonico, espera.plazo)
            espera.futuro.set_result(None)
            await self._ceder()
        self._monotonico = max(self._monotonico, objetivo)

    # --- Internos ---

    def _registrar(self, segundos: float) -> _Espera:
        espera = _Espera(self._monotonico + segundos, next(self._contador), asyncio.get_running_loop().create_future())
        self._esperas.append(espera)
        return espera

    def _quitar(self, espera: _Espera) -> None:
        with contextlib.suppress(ValueError):
            self._esperas.remove(espera)

    @staticmethod
    async def _ceder() -> None:
        for _ in range(_CESIONES):
            await asyncio.sleep(0)

    @staticmethod
    async def _cancelar(tarea: "asyncio.Future") -> None:
        """Cancela la tarea y espera a que termine de cancelarse (como `asyncio.wait_for`)."""
        if not tarea.done():
            tarea.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await tarea


def instalar_reloj_controlable(parche: pytest.MonkeyPatch) -> RelojControlable:
    """Instala un reloj controlable como el reloj del sistema; `parche` lo restaura al deshacerse."""
    from app.utils import reloj as modulo_reloj

    controlable = RelojControlable()
    parche.setattr(modulo_reloj, "_reloj_en_uso", controlable)
    return controlable


@pytest.fixture
def reloj_controlable(monkeypatch) -> RelojControlable:
    """El reloj del sistema pasa a ser uno de tiempo virtual; al terminar la prueba vuelve el real."""
    return instalar_reloj_controlable(monkeypatch)
