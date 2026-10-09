"""Pruebas de T1 (spec 003b, RA-02.11): el Redis simulado controlable.

`RedisControlable` envuelve el servidor de `fakeredis` que ya comparte toda la suite (spec 002) y le da
a la prueba tres poderes: que no responda (error de conexión o de tiempo, o llamada retenida), que pierda
claves (como un desalojo por memoria) y que sus claves caduquen según el tiempo virtual, no el real.
Redis sigue sin usarse de verdad. Ninguna prueba de este archivo espera más de décimas de segundo reales:
los 900 s de caducidad son tiempo virtual. Las claves llevan el prefijo `PRUEBA`; la limpieza automática de
cada prueba vacía el servidor simulado.
"""
import asyncio
import threading

import pytest
import redis
from redis.exceptions import ConnectionError as ErrorDeConexion
from redis.exceptions import TimeoutError as ErrorDeTiempo

from tests.soporte import simulados


# --- (a) Que no responda -----------------------------------------------------------------------

def test_no_responde_conexion_hace_fallar_toda_orden_con_error_de_conexion(redis_controlable):
    """RA-02.11 (a): con `no_responde("conexion")` cualquier orden lanza el error de conexión de `redis`."""
    redis_controlable.set("PRUEBA:a", "1")
    redis_controlable.no_responde("conexion")
    with pytest.raises(ErrorDeConexion):
        redis_controlable.get("PRUEBA:a")
    with pytest.raises(ErrorDeConexion):
        redis_controlable.set("PRUEBA:b", "2")
    with pytest.raises(ErrorDeConexion):
        redis_controlable.execute_command("PING")


def test_no_responde_tiempo_hace_fallar_toda_orden_con_error_de_tiempo(redis_controlable):
    """RA-02.11 (a): con `no_responde("tiempo")` cualquier orden lanza el error de tiempo agotado de `redis`."""
    redis_controlable.no_responde("tiempo")
    with pytest.raises(ErrorDeTiempo):
        redis_controlable.get("PRUEBA:a")
    with pytest.raises(ErrorDeTiempo):
        redis_controlable.incr("PRUEBA:c")


def test_no_responde_tambien_hace_fallar_una_transaccion(redis_controlable):
    """RA-02.11 (a): una transacción (MULTI/EXEC) también falla, tanto la que ya estaba armada como la nueva."""
    tuberia = redis_controlable.pipeline(transaction=True)
    tuberia.set("PRUEBA:t", "1")
    redis_controlable.no_responde("conexion")
    with pytest.raises(ErrorDeConexion):
        tuberia.execute()
    with pytest.raises(ErrorDeConexion):
        with redis_controlable.pipeline(transaction=True) as otra:
            otra.hset("PRUEBA:h", mapping={"a": "1"})
            otra.execute()
    redis_controlable.responder_bien()
    assert redis_controlable.exists("PRUEBA:t") == 0, "la transacción que falló no debe haber escrito nada"


def test_responder_bien_restablece_el_servicio(redis_controlable):
    """RA-02.11 (a): tras `responder_bien()` las órdenes vuelven a funcionar y lo guardado antes sigue ahí."""
    redis_controlable.set("PRUEBA:a", "1")
    redis_controlable.no_responde("tiempo")
    with pytest.raises(ErrorDeTiempo):
        redis_controlable.get("PRUEBA:a")
    redis_controlable.responder_bien()
    assert redis_controlable.get("PRUEBA:a") == "1"
    with redis_controlable.pipeline(transaction=True) as tuberia:
        tuberia.incr("PRUEBA:n")
        assert tuberia.execute() == [1]


def test_un_tipo_de_fallo_desconocido_es_un_error_de_la_prueba(redis_controlable):
    """RA-02.11 (a): `no_responde` solo admite «conexion» y «tiempo»; otro valor es un error de uso claro."""
    with pytest.raises(ValueError):
        redis_controlable.no_responde("lento")
    redis_controlable.set("PRUEBA:a", "1")  # el intento fallido no dejó el servidor sin responder


def test_colgar_retiene_la_llamada_en_otro_hilo_hasta_liberar(redis_controlable):
    """RA-02.11 (a): con `colgar()` la llamada no termina hasta `liberar()`, y entonces se completa con normalidad."""
    redis_controlable.colgar()
    resultado = {}

    def llamar():
        resultado["valor"] = redis_controlable.set("PRUEBA:colgada", "1")

    hilo = threading.Thread(target=llamar, daemon=True)
    hilo.start()
    assert redis_controlable.esperar_retenida(2.0), "la llamada debía quedar retenida"
    hilo.join(0.15)
    assert hilo.is_alive(), "retenida: no puede haber terminado antes de liberar"
    assert "valor" not in resultado
    redis_controlable.liberar()
    hilo.join(2.0)
    assert not hilo.is_alive()
    assert resultado["valor"] is True
    assert redis_controlable.get("PRUEBA:colgada") == "1"


def test_colgar_tiene_un_tope_de_seguridad_que_no_deja_hilos_colgados(redis_controlable, monkeypatch):
    """RA-02.11 (a): si la prueba nunca libera, la llamada se rinde con error de tiempo al agotarse el tope."""
    monkeypatch.setattr(simulados, "TOPE_DE_RETENCION", 0.1)
    redis_controlable.colgar()
    with pytest.raises(ErrorDeTiempo):
        redis_controlable.get("PRUEBA:a")


def test_la_fixture_libera_las_llamadas_retenidas_al_terminar(redis_controlable):
    """RA-02.11 (a): la fixture libera al terminar la prueba (si no, el hilo quedaría vivo hasta el tope)."""
    assert simulados.RedisControlable is type(redis_controlable)
    redis_controlable.colgar()  # el cierre de la fixture libera; la prueba no lo hace a propósito


# --- (b) Perder claves --------------------------------------------------------------------------

def test_perder_borra_una_clave_y_deja_las_demas(redis_controlable):
    """RA-02.11 (b): `perder(clave)` quita solo esa clave, como un desalojo por memoria."""
    redis_controlable.set("PRUEBA:una", "1")
    redis_controlable.set("PRUEBA:otra", "2")
    redis_controlable.perder("PRUEBA:una")
    assert redis_controlable.get("PRUEBA:una") is None
    assert redis_controlable.get("PRUEBA:otra") == "2"
    redis_controlable.perder("PRUEBA:no_existia")  # perder lo que no está no es un error


def test_perder_funciona_aunque_el_servicio_no_responda(redis_controlable):
    """RA-02.11 (b): la pérdida es un efecto del servidor, no una orden del cliente: no la frena `no_responde`."""
    redis_controlable.set("PRUEBA:una", "1")
    redis_controlable.no_responde("conexion")
    redis_controlable.perder("PRUEBA:una")
    redis_controlable.responder_bien()
    assert redis_controlable.get("PRUEBA:una") is None


def test_perder_todas_vacia_el_servidor_simulado(redis_controlable):
    """RA-02.11 (b): `perder_todas()` vacía todas las bases del servidor simulado, no solo la del cliente."""
    redis_controlable.set("PRUEBA:una", "1")
    redis_controlable.hset("PRUEBA:hash", mapping={"a": "1"})
    otra_base = redis.Redis(db=5, decode_responses=True)
    otra_base.set("PRUEBA:otra_base", "x")
    redis_controlable.perder_todas()
    assert redis_controlable.claves("*") == []
    assert otra_base.get("PRUEBA:otra_base") is None


def test_claves_lista_por_patron(redis_controlable):
    """RA-02.11 (b): `claves(patrón)` devuelve las claves que coinciden, como texto y ordenadas."""
    for nombre in ("PRUEBA:r:b", "PRUEBA:r:a", "PRUEBA:x:c"):
        redis_controlable.set(nombre, "1")
    assert redis_controlable.claves("PRUEBA:r:*") == ["PRUEBA:r:a", "PRUEBA:r:b"]
    assert redis_controlable.claves("PRUEBA:x:*") == ["PRUEBA:x:c"]
    assert redis_controlable.claves("PRUEBA:nada:*") == []
    assert redis_controlable.claves() == ["PRUEBA:r:a", "PRUEBA:r:b", "PRUEBA:x:c"]


# --- (c) Caducidad según el tiempo virtual ------------------------------------------------------

def test_avanzar_caduca_segun_el_tiempo_virtual(redis_controlable):
    """RA-02.11 (c): una clave de 900 s vive tras `avanzar(899)` y no tras `avanzar(901)`; la que no caduca no se toca."""
    redis_controlable.set("PRUEBA:caduca", "1", ex=900)
    redis_controlable.set("PRUEBA:eterna", "2")
    redis_controlable.set("PRUEBA:corta", "3", ex=60)
    redis_controlable.avanzar(899)
    assert redis_controlable.get("PRUEBA:caduca") == "1"
    assert redis_controlable.get("PRUEBA:corta") is None
    assert 0 < redis_controlable.ttl("PRUEBA:caduca") <= 1
    redis_controlable.avanzar(2)  # 901 s en total
    assert redis_controlable.get("PRUEBA:caduca") is None
    assert redis_controlable.get("PRUEBA:eterna") == "2"
    assert redis_controlable.ttl("PRUEBA:eterna") == -1


def test_avanzar_tambien_caduca_los_campos_de_un_hash_con_caducidad(redis_controlable):
    """RA-02.11 (c): el estado de la recuperación es un hash con caducidad: caduca entero, igual que en Redis."""
    redis_controlable.hset("PRUEBA:estado", mapping={"intentos": "0", "codigo": "x"})
    redis_controlable.expire("PRUEBA:estado", 900)
    redis_controlable.avanzar(899)
    assert redis_controlable.hget("PRUEBA:estado", "intentos") == "0"
    redis_controlable.avanzar(2)
    assert redis_controlable.exists("PRUEBA:estado") == 0


def test_avanzar_es_acumulativo(redis_controlable):
    """RA-02.11 (c): dos avances seguidos suman (60 + 60 s caducan una clave de 100 s)."""
    redis_controlable.set("PRUEBA:k", "1", ex=100)
    redis_controlable.avanzar(60)
    assert redis_controlable.exists("PRUEBA:k") == 1
    redis_controlable.avanzar(60)
    assert redis_controlable.exists("PRUEBA:k") == 0


def test_avanzar_no_gasta_tiempo_real(redis_controlable):
    """RA-02.11 (c): una hora virtual no cuesta tiempo real y no se puede retroceder."""
    import time

    redis_controlable.set("PRUEBA:k", "1", ex=3600)
    inicio = time.monotonic()
    redis_controlable.avanzar(3599)
    assert time.monotonic() - inicio < 0.5
    assert redis_controlable.exists("PRUEBA:k") == 1
    with pytest.raises(ValueError):
        redis_controlable.avanzar(-1)


def test_avanzar_funciona_aunque_el_servicio_no_responda(redis_controlable):
    """RA-02.11 (c): el tiempo pasa en el servidor aunque el cliente no pueda hablarle."""
    redis_controlable.set("PRUEBA:k", "1", ex=10)
    redis_controlable.no_responde("conexion")
    redis_controlable.avanzar(11)
    redis_controlable.responder_bien()
    assert redis_controlable.exists("PRUEBA:k") == 0


def test_avanzar_caduca_las_claves_de_todas_las_bases(redis_controlable):
    """RA-02.11 (c): el tiempo es del servidor: también caducan las claves de otra base numerada."""
    otra_base = redis.Redis(db=5, decode_responses=True)
    otra_base.set("PRUEBA:otra", "1", ex=30)
    redis_controlable.avanzar(31)
    assert otra_base.get("PRUEBA:otra") is None


def test_vincular_reloj_une_el_reloj_controlable_con_la_caducidad(redis_controlable, reloj_controlable):
    """RA-02.11 (c): tras `vincular_reloj`, `await reloj.avanzar(s)` también caduca las claves y adelanta el reloj."""
    redis_controlable.vincular_reloj(reloj_controlable)
    redis_controlable.set("PRUEBA:k", "1", ex=900)
    antes = reloj_controlable.monotonico()

    asyncio.run(reloj_controlable.avanzar(899))
    assert redis_controlable.exists("PRUEBA:k") == 1
    assert reloj_controlable.monotonico() - antes == pytest.approx(899)
    asyncio.run(reloj_controlable.avanzar(2))
    assert redis_controlable.exists("PRUEBA:k") == 0
    assert reloj_controlable.monotonico() - antes == pytest.approx(901)


def test_sin_vincular_el_reloj_no_toca_las_claves(redis_controlable, reloj_controlable):
    """RA-02.11 (c): vincular es explícito; sin él, el reloj y el Redis simulado avanzan por separado."""
    redis_controlable.set("PRUEBA:k", "1", ex=10)
    asyncio.run(reloj_controlable.avanzar(60))
    assert redis_controlable.exists("PRUEBA:k") == 1


def test_la_vinculacion_se_deshace_al_terminar_la_prueba(redis_controlable, reloj_controlable):
    """RA-02.11 (c): `desvincular_reloj()` (que llama la fixture al cerrar) devuelve al reloj su `avanzar` original."""
    original = reloj_controlable.avanzar
    redis_controlable.vincular_reloj(reloj_controlable)
    assert reloj_controlable.avanzar != original
    redis_controlable.desvincular_reloj()
    assert reloj_controlable.avanzar == original


# --- (d) El cliente es el servidor compartido ------------------------------------------------------

def test_el_cliente_comparte_el_servidor_simulado_de_la_suite(redis_controlable):
    """RA-02.11 (d): lo que escribe el cliente controlable lo ve cualquier otro cliente de la misma base, y viceversa."""
    otro = redis.Redis.from_url("redis://cualquiera.invalid:6379/3", decode_responses=True)
    redis_controlable.set("PRUEBA:compartida", "desde_el_controlable")
    assert otro.get("PRUEBA:compartida") == "desde_el_controlable"
    otro.set("PRUEBA:de_otro", "valor")
    assert redis_controlable.get("PRUEBA:de_otro") == "valor"
    # Otra base numerada es independiente, como en Redis.
    assert redis.Redis(db=0, decode_responses=True).get("PRUEBA:compartida") is None


def test_el_cliente_es_un_cliente_del_simulado_y_no_abre_red(redis_controlable):
    """RA-02.11 (d): es un `FakeRedis` del mismo servidor que instaló la suite, nunca el Redis real."""
    import fakeredis

    assert isinstance(redis_controlable.cliente, fakeredis.FakeRedis)
    assert redis_controlable.cliente.connection_pool.connection_kwargs.get("server") is simulados._estado["servidor_redis"]


def test_flushall_de_la_limpieza_vacia_lo_que_deja_el_controlable(redis_controlable):
    """RA-02.11 (d): lo mismo que usa la limpieza de cada prueba (`redis.Redis().flushall()`) vacía este cliente."""
    redis_controlable.set("PRUEBA:k", "1")
    redis_controlable.hset("PRUEBA:h", mapping={"a": "1"})
    redis.Redis().flushall()
    assert redis_controlable.claves("*") == []


def test_las_claves_de_una_prueba_no_pasan_a_la_siguiente_parte_1(redis_controlable):
    """RA-02.11 (d): la limpieza automática vacía el servidor entre pruebas (esta deja una clave; la parte 2 no la ve)."""
    redis_controlable.set("PRUEBA:residuo", "1", ex=5000)


def test_las_claves_de_una_prueba_no_pasan_a_la_siguiente_parte_2(redis_controlable):
    """RA-02.11 (d): complementa la parte 1 (también en `--orden-inverso`: ninguna depende de la otra)."""
    assert redis_controlable.get("PRUEBA:residuo") is None


# --- (e) Humo de las órdenes que usará la recuperación -----------------------------------------------

def test_humo_set_nx_ex(redis_controlable):
    """RA-02.11 (e): `SET` con `NX` y `EX`: la segunda no pisa a la primera y la clave lleva su caducidad."""
    assert redis_controlable.set("PRUEBA:bloqueo", "1", nx=True, ex=60) is True
    assert redis_controlable.set("PRUEBA:bloqueo", "2", nx=True, ex=60) is None
    assert redis_controlable.get("PRUEBA:bloqueo") == "1"
    assert 0 < redis_controlable.ttl("PRUEBA:bloqueo") <= 60


def test_humo_incr_y_expire_nx(redis_controlable):
    """RA-02.11 (e): `INCR` y `EXPIRE ... NX`: la ventana fija solo se fija la primera vez."""
    assert redis_controlable.incr("PRUEBA:contador") == 1
    assert redis_controlable.expire("PRUEBA:contador", 3600, nx=True) is True
    redis_controlable.avanzar(1000)
    assert redis_controlable.incr("PRUEBA:contador") == 2
    assert redis_controlable.expire("PRUEBA:contador", 3600, nx=True) is False, "ya tenía caducidad: no se reinicia"
    restante = redis_controlable.ttl("PRUEBA:contador")
    assert 2500 <= restante <= 2600, f"la ventana debía conservar lo que le quedaba (3600 - 1000), quedó {restante}"


def test_humo_hset_mapping_hincrby_hmget(redis_controlable):
    """RA-02.11 (e): `HSET` con `mapping`, `HINCRBY` y `HMGET` (el estado de la recuperación es un hash)."""
    redis_controlable.hset("PRUEBA:estado", mapping={"codigo": "x", "intentos": "0", "emision": "10"})
    assert redis_controlable.hincrby("PRUEBA:estado", "intentos", 1) == 1
    assert redis_controlable.hincrby("PRUEBA:estado", "intentos", -1) == 0
    assert redis_controlable.hmget("PRUEBA:estado", ["codigo", "intentos", "no_existe"]) == ["x", "0", None]


def test_humo_del_ttl_y_pttl(redis_controlable):
    """RA-02.11 (e): `DEL` devuelve cuántas borró (0 la segunda vez); `TTL` y `PTTL` distinguen sin clave y sin caducidad."""
    redis_controlable.set("PRUEBA:k", "1", ex=100)
    assert 0 < redis_controlable.ttl("PRUEBA:k") <= 100
    assert 0 < redis_controlable.pttl("PRUEBA:k") <= 100_000
    assert redis_controlable.delete("PRUEBA:k") == 1
    assert redis_controlable.delete("PRUEBA:k") == 0
    assert redis_controlable.ttl("PRUEBA:k") == -2
    assert redis_controlable.pttl("PRUEBA:k") == -2
    redis_controlable.set("PRUEBA:sin_caducidad", "1")
    assert redis_controlable.ttl("PRUEBA:sin_caducidad") == -1


def test_humo_de_una_transaccion_multi_exec(redis_controlable):
    """RA-02.11 (e): una transacción crea el hash y su caducidad juntos y devuelve las respuestas en orden."""
    with redis_controlable.pipeline(transaction=True) as tuberia:
        tuberia.delete("PRUEBA:estado")
        tuberia.hset("PRUEBA:estado", mapping={"codigo": "x", "intentos": "0"})
        tuberia.expire("PRUEBA:estado", 900)
        respuestas = tuberia.execute()
    assert respuestas == [0, 2, True]
    assert redis_controlable.hgetall("PRUEBA:estado") == {"codigo": "x", "intentos": "0"}
    assert 0 < redis_controlable.ttl("PRUEBA:estado") <= 900
