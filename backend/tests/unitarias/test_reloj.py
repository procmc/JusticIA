"""Pruebas de T1 (spec 003a, RA-02.9): el reloj controlable.

El sistema obtiene la hora y mide plazos a través de un reloj. En producción es el real
(`RelojReal`); en las pruebas lo adelanta la prueba a voluntad (`RelojControlable`, fixture
`reloj_controlable`), sin dependencias nuevas y sin esperar tiempo real. Ninguna prueba de este
archivo espera más de décimas de segundo reales: los plazos de 5, 15 y 20 s son tiempo virtual.
"""
import asyncio
import time
from datetime import datetime, timedelta

import pytest

from app.utils.reloj import RelojReal, obtener_reloj
from tests.soporte.reloj import RelojControlable, instalar_reloj_controlable


# --- El reloj real (RA-02.9) -------------------------------------------------------------------

def test_el_monotonico_real_crece_con_el_tiempo_real():
    """RA-02.9: tras una pausa de centésimas, `monotonico()` crece al menos esa pausa."""
    reloj = RelojReal()
    antes = reloj.monotonico()
    time.sleep(0.03)
    assert reloj.monotonico() - antes >= 0.025


def test_la_hora_real_es_utc_con_zona():
    """RA-02.9: `ahora()` devuelve un `datetime` consciente de zona, en UTC, y cercano a la hora del sistema."""
    ahora = RelojReal().ahora()
    assert isinstance(ahora, datetime)
    assert ahora.tzinfo is not None
    assert ahora.utcoffset() == timedelta(0)
    assert abs((datetime.now(ahora.tzinfo) - ahora).total_seconds()) < 5


def test_dormir_real_espera_de_verdad():
    """RA-02.9: `dormir()` del reloj real tarda el plazo (décimas de segundo)."""
    reloj = RelojReal()

    async def escenario():
        antes = reloj.monotonico()
        await reloj.dormir(0.05)
        return reloj.monotonico() - antes

    assert asyncio.run(escenario()) >= 0.045


def test_con_limite_real_devuelve_el_resultado_a_tiempo():
    """RA-02.9: una corrutina que termina antes del plazo devuelve su valor."""
    reloj = RelojReal()

    async def rapida():
        await asyncio.sleep(0.01)
        return "listo PRUEBA"

    assert asyncio.run(reloj.con_limite(rapida(), 5)) == "listo PRUEBA"


def test_con_limite_real_lanza_timeouterror_con_un_plazo_de_decimas():
    """RA-02.9: pasado el plazo, `con_limite()` lanza `TimeoutError`."""
    reloj = RelojReal()

    async def lenta():
        await asyncio.sleep(30)

    with pytest.raises(TimeoutError):
        asyncio.run(reloj.con_limite(lenta(), 0.05))


# --- El reloj controlable (RA-02.9) ------------------------------------------------------------

def test_avanzar_cambia_exactamente_el_monotonico_y_la_hora():
    """RA-02.9: `avanzar(5)` suma exactamente 5 s a `monotonico()` y a `ahora()`."""
    reloj = RelojControlable()
    monotonico, ahora = reloj.monotonico(), reloj.ahora()

    asyncio.run(reloj.avanzar(5))

    assert reloj.monotonico() - monotonico == 5
    assert reloj.ahora() - ahora == timedelta(seconds=5)
    assert reloj.ahora().tzinfo is not None and reloj.ahora().utcoffset() == timedelta(0)


def test_el_reloj_controlable_no_avanza_solo():
    """RA-02.9: sin `avanzar`, el tiempo virtual no se mueve aunque pase tiempo real."""
    reloj = RelojControlable()
    monotonico, ahora = reloj.monotonico(), reloj.ahora()
    time.sleep(0.02)
    assert reloj.monotonico() == monotonico
    assert reloj.ahora() == ahora


def test_dormir_sigue_pendiente_a_los_4_9_s_y_termina_a_los_5():
    """RA-02.9: `dormir(5)` no termina a los 4,9 s virtuales y sí a los 5,0."""
    reloj = RelojControlable()

    async def escenario():
        tarea = asyncio.ensure_future(reloj.dormir(5))
        await reloj.avanzar(4.9)
        pendiente_a_los_4_9 = not tarea.done()
        await reloj.avanzar(0.1)
        return pendiente_a_los_4_9, tarea.done()

    assert asyncio.run(escenario()) == (True, True)


def test_con_limite_sigue_pendiente_a_los_14_9_s_y_lanza_timeouterror_a_los_15():
    """RA-02.9: el plazo de 15 s falla justo a los 15,0 s virtuales y cancela la tarea interna."""
    reloj = RelojControlable()
    registro = {"cancelada": False}

    async def interna():
        try:
            await reloj.dormir(100)
        except asyncio.CancelledError:
            registro["cancelada"] = True
            raise

    async def escenario():
        tarea = asyncio.ensure_future(reloj.con_limite(interna(), 15))
        await reloj.avanzar(14.9)
        pendiente_a_los_14_9 = not tarea.done()
        sin_cancelar_aun = not registro["cancelada"]
        await reloj.avanzar(0.1)
        terminada = tarea.done()
        # Si no terminó, no se espera (colgaría la prueba): la aserción de abajo ya falla.
        lanzo_timeout = terminada and isinstance(tarea.exception(), TimeoutError)
        # Se mide aquí y no al cerrar el bucle, que cancelaría cualquier tarea que hubiera quedado viva.
        return pendiente_a_los_14_9, sin_cancelar_aun, terminada, lanzo_timeout, registro["cancelada"]

    assert asyncio.run(escenario()) == (True, True, True, True, True)
    assert reloj.esperas_pendientes == 0


def test_una_corrutina_que_termina_antes_del_plazo_devuelve_su_valor():
    """RA-02.9: si la corrutina termina antes del plazo, `con_limite()` devuelve su valor y no deja esperas."""
    reloj = RelojControlable()

    async def interna():
        await reloj.dormir(3)
        return "valor PRUEBA"

    async def escenario():
        tarea = asyncio.ensure_future(reloj.con_limite(interna(), 15))
        await reloj.avanzar(3)
        terminada = tarea.done()
        return terminada, (tarea.result() if terminada else None)

    assert asyncio.run(escenario()) == (True, "valor PRUEBA")
    assert reloj.esperas_pendientes == 0


def test_una_espera_cancelada_se_des_registra():
    """RA-02.9: cancelar una espera la quita de las pendientes y `avanzar` ya no la despierta."""
    reloj = RelojControlable()

    async def escenario():
        tarea = asyncio.ensure_future(reloj.dormir(5))
        await reloj.avanzar(1)
        registradas = reloj.esperas_pendientes
        tarea.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarea
        return registradas, reloj.esperas_pendientes

    assert asyncio.run(escenario()) == (1, 0)


def test_cancelar_un_con_limite_cancela_la_tarea_interna_y_des_registra_el_plazo():
    """RA-02.9: si cancelan a quien espera dentro de `con_limite`, la tarea interna se cancela y no quedan esperas."""
    reloj = RelojControlable()
    registro = {"cancelada": False}

    async def interna():
        try:
            await reloj.dormir(100)
        except asyncio.CancelledError:
            registro["cancelada"] = True
            raise

    async def escenario():
        tarea = asyncio.ensure_future(reloj.con_limite(interna(), 15))
        await reloj.avanzar(1)
        tarea.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tarea
        return registro["cancelada"]  # medido antes de que el cierre del bucle cancele lo que siga vivo

    assert asyncio.run(escenario()) is True
    assert reloj.esperas_pendientes == 0


def test_cuatro_esperas_de_5_s_seguidas_piden_20_s():
    """RA-02.9: el reloj registra la siguiente espera de la corrutina; cuatro de 5 s necesitan 20 s en total."""
    reloj = RelojControlable()

    async def cuatro_operaciones():
        for _ in range(4):
            await reloj.dormir(5)

    async def escenario():
        tarea = asyncio.ensure_future(cuatro_operaciones())
        await reloj.avanzar(19.9)
        pendiente_a_los_19_9 = not tarea.done()
        await reloj.avanzar(0.1)
        return pendiente_a_los_19_9, tarea.done()

    assert asyncio.run(escenario()) == (True, True)


def test_cuatro_esperas_de_5_s_no_caben_en_un_limite_de_15_s():
    """RA-02.9: el límite es TOTAL; con operaciones de 5 s el plazo de 15 s corta a la tercera."""
    reloj = RelojControlable()
    terminadas = []

    async def cuatro_operaciones():
        for numero in range(4):
            await reloj.dormir(5)
            terminadas.append(numero)

    async def escenario():
        tarea = asyncio.ensure_future(reloj.con_limite(cuatro_operaciones(), 15))
        await reloj.avanzar(15)
        return tarea.done() and isinstance(tarea.exception(), TimeoutError)

    assert asyncio.run(escenario()) is True
    assert terminadas == [0, 1]  # la tercera operación coincide con el plazo y queda cortada


# --- Qué reloj se usa (RA-02.9) -----------------------------------------------------------------

def test_sin_la_fixture_el_reloj_en_uso_es_el_real():
    """RA-02.9: por omisión `obtener_reloj()` devuelve el reloj real."""
    assert isinstance(obtener_reloj(), RelojReal)


def test_con_la_fixture_el_reloj_en_uso_es_el_controlable(reloj_controlable):
    """RA-02.9: con `reloj_controlable`, todo el sistema obtiene ese reloj por `obtener_reloj()`."""
    assert isinstance(reloj_controlable, RelojControlable)
    assert obtener_reloj() is reloj_controlable


def test_el_reloj_instalado_se_restaura_al_terminar():
    """RA-02.9: al terminar, `monkeypatch` devuelve el reloj real (no queda estado compartido)."""
    with pytest.MonkeyPatch.context() as parche:
        instalado = instalar_reloj_controlable(parche)
        assert obtener_reloj() is instalado
    assert isinstance(obtener_reloj(), RelojReal)
