"""Pruebas de T4 (spec 003b): el almacén de estado y de límites de la recuperación, en Redis.

Cubren RF-03.4 (el código vive 15 min) y RF-03.7 (la verificación, 10 min), RF-03.9 (el contador de intentos es
atómico), RF-03.10 a RF-03.12 (una solicitud por minuto, cinco por hora, por correo), RF-03.20 (tiempo de espera
fijo y falla cerrada) y RF-03.25 (si Redis pierde una clave, el proceso se rechaza). El repositorio es el único
módulo que habla con Redis en la recuperación (`app/repositories/recuperacion_estado_repository.py`).

Todo corre sobre el Redis simulado y controlable (`redis_controlable`, T1): los plazos de minutos y horas son tiempo
VIRTUAL (`avanzar`), así que ninguna prueba espera más que décimas de segundo reales. Los hilos usan una barrera para
que arranquen a la vez. Los correos y los códigos son inventados (prefijo `prueba`); el secreto de las claves derivadas
es un texto sintético FIJO, a propósito: así lo que se busca en Redis (el código, el correo) no puede coincidir por
azar con un fragmento de un resumen, y la prueba no es inestable.
"""
import hashlib
import importlib
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytest
import redis
from redis.exceptions import ConnectionError as ErrorDeConexion
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as ErrorDeTiempo

from app.utils import recuperacion_codigos as rc

CORREO = "prueba.almacen@prueba.invalid"


def _codigo_derivado(etiqueta: bytes) -> str:
    """Un código de 6 dígitos inventado y estable: sale de una etiqueta, así ningún código queda escrito en el archivo."""
    return f"{int.from_bytes(hashlib.sha256(etiqueta).digest()[:8], 'big') % 10 ** 6:06d}"


CODIGO = _codigo_derivado(b"PRUEBA codigo valido del almacen")
CODIGO_INCORRECTO = _codigo_derivado(b"PRUEBA codigo incorrecto del almacen")
CEDULA = "PRUEBA0001"
VINCULO = "ab" * 32
SECRETO_SINTETICO = "PRUEBA-secreto-sintetico-solo-para-las-pruebas-del-almacen"


@pytest.fixture
def almacen():
    """El módulo del repositorio. Se importa aquí para que, si todavía no existe, cada prueba falle por su cuenta."""
    return importlib.import_module("app.repositories.recuperacion_estado_repository")


@pytest.fixture
def claves():
    return rc.derivar_claves_de_recuperacion(SECRETO_SINTETICO)


@pytest.fixture
def huella(claves):
    return rc.huella_de_correo(claves.huella, CORREO)


def _hash_del_codigo(claves, huella, codigo=CODIGO):
    return rc.hash_de_codigo(claves.codigo, huella, codigo)


def _guardar_estado(almacen, claves, huella, codigo=CODIGO, cedula=CEDULA, vinculo=VINCULO, emision="emision-de-prueba"):
    almacen.guardar_estado(huella, _hash_del_codigo(claves, huella, codigo), emision, cedula, vinculo)
    return emision


def _verificar(almacen, claves, huella, codigo):
    """El paso 2 de la recuperación (plan §3.4) reducido a lo que decide el almacén: qué dice cada intento."""
    intento = almacen.registrar_intento(huella)
    if intento is None:
        return "vencido"
    if intento.numero > 5:
        return "invalidado"
    if _hash_del_codigo(claves, huella, codigo) != intento.estado.hash_codigo:
        return "invalidado" if intento.numero >= 5 else "incorrecto"
    return "aprobado"


def _en_paralelo(cantidad, tarea):
    """Ejecuta `tarea(i)` en `cantidad` hilos que arrancan a la vez (barrera) y devuelve sus resultados en orden."""
    barrera = threading.Barrier(cantidad)

    def correr(i):
        barrera.wait(timeout=5)
        return tarea(i)

    with ThreadPoolExecutor(max_workers=cantidad) as pool:
        futuros = [pool.submit(correr, i) for i in range(cantidad)]
        return [futuro.result(timeout=10) for futuro in futuros]


def _volcado_del_servidor():
    """Todas las claves y todos los valores de todas las bases del servidor simulado, como texto."""
    textos = []
    for base in range(16):
        cliente = redis.Redis(db=base, decode_responses=True)
        for clave in cliente.scan_iter():
            textos.append(clave)
            tipo = cliente.type(clave)
            if tipo == "hash":
                for campo, valor in cliente.hgetall(clave).items():
                    textos.extend((campo, valor))
            elif tipo == "string":
                textos.append(cliente.get(clave))
    return textos


# --- La fixture parcha el cliente del repositorio -------------------------------------------------------------------

def test_la_fixture_hace_que_el_repositorio_use_el_cliente_controlable(almacen, redis_controlable):
    """RA-02.11 / RF-03.20: con `redis_controlable`, el repositorio habla con el Redis simulado que la prueba controla."""
    assert almacen.obtener_cliente() is redis_controlable.cliente


# --- RF-03.4: el estado (código + contador + caducidad) es una sola unidad -----------------------------------------

def test_guardar_estado_crea_los_cinco_campos_y_la_caducidad_juntos(almacen, redis_controlable, claves, huella):
    """RF-03.4: el hash de la solicitud lleva sus cinco campos y su caducidad de 15 minutos desde el primer instante."""
    emision = _guardar_estado(almacen, claves, huella)
    clave = f"recuperacion:estado:{huella}"
    assert redis_controlable.claves("*") == [clave]
    assert redis_controlable.type(clave) == "hash"
    assert redis_controlable.hgetall(clave) == {
        "codigo": _hash_del_codigo(claves, huella),
        "intentos": "0",
        "emision": emision,
        "cedula": CEDULA,
        "vinculo": VINCULO,
    }
    assert 899 <= redis_controlable.ttl(clave) <= 900


def test_guardar_estado_de_un_correo_sin_cuenta_conserva_los_cinco_campos(almacen, redis_controlable, claves, huella):
    """RF-03.8: el estado señuelo (sin cédula) tiene el mismo aspecto: el campo `cedula` existe, vacío."""
    _guardar_estado(almacen, claves, huella, cedula="")
    assert set(redis_controlable.hgetall(f"recuperacion:estado:{huella}")) == {"codigo", "intentos", "emision", "cedula", "vinculo"}
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "cedula") == ""


def test_guardar_estado_es_una_sola_transaccion(almacen, redis_controlable, claves, huella, monkeypatch):
    """RF-03.4 / RF-03.9: borrar, escribir los campos y fijar la caducidad viajan en una transacción (MULTI/EXEC)."""
    llamadas = []
    original = redis_controlable.cliente.pipeline

    def espia(*args, **kwargs):
        llamadas.append(kwargs.get("transaction", args[0] if args else True))
        return original(*args, **kwargs)

    monkeypatch.setattr(redis_controlable.cliente, "pipeline", espia)
    _guardar_estado(almacen, claves, huella)
    assert llamadas == [True]


def test_guardar_estado_reemplaza_el_estado_anterior_entero(almacen, redis_controlable, claves, huella):
    """RF-03.4: pedir un código nuevo borra el estado anterior completo (campos, contador y caducidad), no lo mezcla."""
    clave = f"recuperacion:estado:{huella}"
    redis_controlable.hset(clave, mapping={"codigo": "viejo", "intentos": "4", "emision": "vieja", "cedula": "x", "vinculo": "y", "sobrante": "z"})
    redis_controlable.expire(clave, 100)
    emision = _guardar_estado(almacen, claves, huella, emision="emision-nueva")
    assert redis_controlable.hgetall(clave) == {
        "codigo": _hash_del_codigo(claves, huella),
        "intentos": "0",
        "emision": emision,
        "cedula": CEDULA,
        "vinculo": VINCULO,
    }, "no debe quedar ningún campo del estado anterior"
    assert 899 <= redis_controlable.ttl(clave) <= 900, "la caducidad parte de nuevo, no hereda los 100 s anteriores"


@pytest.mark.parametrize("segundos, vive", [(899, True), (901, False)])
def test_el_estado_vive_15_minutos(almacen, redis_controlable, claves, huella, segundos, vive):
    """RF-03.4: el código sirve a los 14 min 59 s y ya no a los 15 min 1 s."""
    _guardar_estado(almacen, claves, huella)
    redis_controlable.avanzar(segundos)
    assert (redis_controlable.exists(f"recuperacion:estado:{huella}") == 1) is vive


@pytest.mark.parametrize("segundos, vive", [(599, True), (601, False)])
def test_la_verificacion_vive_10_minutos(almacen, redis_controlable, huella, segundos, vive):
    """RF-03.7: el cambio de contraseña se permite a los 9 min 59 s y ya no a los 10 min 1 s."""
    almacen.guardar_verificacion(huella, "hash-del-secreto", CEDULA, VINCULO)
    redis_controlable.avanzar(segundos)
    assert (almacen.leer_verificacion(huella) is not None) is vive
    assert (redis_controlable.exists(f"recuperacion:verificacion:{huella}") == 1) is vive


# --- RF-03.1 / RNF-08: ni el código ni el correo quedan en Redis -----------------------------------------------------

def test_ni_el_codigo_ni_el_correo_aparecen_en_ninguna_clave_ni_valor(almacen, redis_controlable, claves, huella):
    """RF-03.1 / RNF-08.1: se recorre TODO el servidor tras todas las operaciones; solo hay huellas y resúmenes (HMAC)."""
    _guardar_estado(almacen, claves, huella)
    almacen.registrar_intento(huella)
    assert almacen.aceptar_solicitud(huella) is True
    almacen.guardar_verificacion(huella, rc.hash_de_secreto(claves.verificacion, rc.generar_secreto()), CEDULA, VINCULO)
    volcado = _volcado_del_servidor()
    assert len(redis_controlable.claves("*")) == 4, "debe haber estado, bloqueo, contador por hora y verificación"
    assert any(huella in texto for texto in volcado), "control positivo: la huella sí está en las claves"
    local, dominio = CORREO.split("@")
    for texto in volcado:
        assert CODIGO not in texto
        assert CORREO not in texto and local not in texto and dominio not in texto


# --- RF-03.9: el contador de intentos es atómico ---------------------------------------------------------------------

def test_cuatro_fallos_y_el_quinto_con_el_codigo_es_aprobado(almacen, redis_controlable, claves, huella):
    """RF-03.9: el quinto intento todavía cuenta como uno de los cinco permitidos."""
    _guardar_estado(almacen, claves, huella)
    resultados = [_verificar(almacen, claves, huella, CODIGO_INCORRECTO) for _ in range(4)]
    resultados.append(_verificar(almacen, claves, huella, CODIGO))
    assert resultados == ["incorrecto"] * 4 + ["aprobado"]
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "intentos") == "5"


def test_cinco_fallos_y_el_sexto_con_el_codigo_es_invalidado(almacen, redis_controlable, claves, huella):
    """RF-03.9: el quinto fallo invalida el código; el sexto, aunque sea el correcto, ya no comprueba y el contador se queda en 5."""
    _guardar_estado(almacen, claves, huella)
    resultados = [_verificar(almacen, claves, huella, CODIGO_INCORRECTO) for _ in range(5)]
    resultados.append(_verificar(almacen, claves, huella, CODIGO))
    resultados.append(_verificar(almacen, claves, huella, CODIGO))
    assert resultados == ["incorrecto"] * 4 + ["invalidado"] * 3  # el quinto fallo y los dos intentos siguientes
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "intentos") == "5", "el intento rechazado se devuelve"


def test_registrar_intento_devuelve_el_numero_de_intento_y_los_datos_del_estado(almacen, redis_controlable, claves, huella):
    """RF-03.9: cada llamada devuelve su número de intento (1, 2, 3...) junto con lo guardado en la solicitud."""
    emision = _guardar_estado(almacen, claves, huella)
    for esperado in (1, 2, 3):
        intento = almacen.registrar_intento(huella)
        assert intento.numero == esperado
        assert intento.estado.hash_codigo == _hash_del_codigo(claves, huella)
        assert intento.estado.emision == emision
        assert intento.estado.cedula == CEDULA
        assert intento.estado.vinculo == VINCULO
    assert almacen.registrar_intento(huella).numero == 4


def test_registrar_intento_conserva_la_caducidad_del_estado(almacen, redis_controlable, claves, huella):
    """RF-03.4: contar intentos no reinicia ni quita la caducidad de 15 minutos."""
    _guardar_estado(almacen, claves, huella)
    redis_controlable.avanzar(300)
    almacen.registrar_intento(huella)
    assert 590 <= redis_controlable.ttl(f"recuperacion:estado:{huella}") <= 600


def test_veinte_intentos_en_paralelo_dejan_el_contador_en_cinco_y_solo_cinco_comprueban(almacen, redis_controlable, claves, huella):
    """RF-03.9: aunque lleguen 20 verificaciones a la vez, solo cinco llegan a comprobar el código y el contador queda en 5."""
    _guardar_estado(almacen, claves, huella)
    intentos = _en_paralelo(20, lambda _: almacen.registrar_intento(huella))
    assert all(intento is not None for intento in intentos)
    comprueban = sorted(intento.numero for intento in intentos if intento.numero <= 5)
    assert comprueban == [1, 2, 3, 4, 5], "cada número de intento permitido lo recibe una sola petición"
    assert sum(1 for intento in intentos if intento.numero > 5) == 15
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "intentos") == "5"


def test_veinte_verificaciones_correctas_en_paralelo_aprueban_a_cinco_y_invalidan_al_resto(almacen, redis_controlable, claves, huella):
    """RF-03.9: con el código correcto en las 20, solo cinco se aprueban; las otras 15 se rechazan por intentos."""
    _guardar_estado(almacen, claves, huella)
    resultados = Counter(_en_paralelo(20, lambda _: _verificar(almacen, claves, huella, CODIGO)))
    assert resultados == {"aprobado": 5, "invalidado": 15}
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "intentos") == "5"


def test_un_estado_nuevo_reinicia_el_contador(almacen, redis_controlable, claves, huella):
    """RF-03.9: pedir otro código empieza de cero: el contador no se hereda."""
    _guardar_estado(almacen, claves, huella)
    for _ in range(5):
        almacen.registrar_intento(huella)
    _guardar_estado(almacen, claves, huella, emision="emision-nueva")
    assert redis_controlable.hget(f"recuperacion:estado:{huella}", "intentos") == "0"
    assert almacen.registrar_intento(huella).numero == 1


def test_sin_estado_registrar_intento_no_devuelve_nada_y_no_deja_ninguna_clave(almacen, redis_controlable, huella):
    """RF-03.25: si Redis perdió el estado, no hay nada que comprobar y el intento NO crea un contador huérfano sin caducidad."""
    assert almacen.registrar_intento(huella) is None
    assert redis_controlable.claves("*") == []


def test_estado_caducado_se_comporta_como_estado_perdido(almacen, redis_controlable, claves, huella):
    """RF-03.4 / RF-03.25: pasados los 15 minutos, registrar un intento devuelve nada y tampoco deja claves."""
    _guardar_estado(almacen, claves, huella)
    redis_controlable.avanzar(901)
    assert almacen.registrar_intento(huella) is None
    assert redis_controlable.claves("*") == []


def test_perder_el_estado_a_mitad_de_camino_no_deja_ninguna_clave(almacen, redis_controlable, claves, huella):
    """RF-03.25: Redis desaloja el estado entre dos intentos; el siguiente devuelve nada y la clave no reaparece."""
    _guardar_estado(almacen, claves, huella)
    almacen.registrar_intento(huella)
    redis_controlable.perder(f"recuperacion:estado:{huella}")
    assert almacen.registrar_intento(huella) is None
    assert redis_controlable.claves("*") == []


def test_perder_el_estado_justo_al_devolver_un_intento_no_deja_un_contador_huerfano(almacen, redis_controlable, claves, huella, monkeypatch):
    """RF-03.25: si el estado se pierde entre contar un intento de más y devolverlo, tampoco queda una clave sin caducidad."""
    _guardar_estado(almacen, claves, huella)
    for _ in range(5):
        almacen.registrar_intento(huella)
    original = redis_controlable.cliente.pipeline
    transacciones = []

    def espia(*args, **kwargs):
        tuberia = original(*args, **kwargs)
        ejecutar = tuberia.execute

        def execute(*a, **k):
            resultado = ejecutar(*a, **k)
            transacciones.append(resultado)
            if len(transacciones) == 1:  # tras contar el sexto intento, Redis desaloja el estado
                redis_controlable.perder(f"recuperacion:estado:{huella}")
            return resultado

        tuberia.execute = execute
        return tuberia

    monkeypatch.setattr(redis_controlable.cliente, "pipeline", espia)
    assert almacen.registrar_intento(huella).numero == 6
    assert redis_controlable.claves("*") == []


# --- RF-03.10, 03.11: una solicitud por minuto, cinco por hora --------------------------------------------------------

def test_solicitud_aceptada_a_0_s_bloqueada_a_59_s_y_aceptada_a_61_s(almacen, redis_controlable, huella):
    """RF-03.10: una solicitud por minuto para el mismo correo."""
    assert almacen.aceptar_solicitud(huella) is True
    redis_controlable.avanzar(59)
    assert almacen.aceptar_solicitud(huella) is False
    redis_controlable.avanzar(2)  # 61 s
    assert almacen.aceptar_solicitud(huella) is True


def test_las_solicitudes_bloqueadas_no_mueven_el_plazo(almacen, redis_controlable, huella):
    """RF-03.10: pedir a los 10, 30 y 50 s no alarga el minuto: a los 61 s desde la ACEPTADA ya se acepta."""
    assert almacen.aceptar_solicitud(huella) is True
    asignado = redis_controlable.ttl(f"recuperacion:bloqueo:{huella}")
    resultados = []
    for adelanto in (10, 20, 20):  # 10, 30 y 50 s
        redis_controlable.avanzar(adelanto)
        resultados.append(almacen.aceptar_solicitud(huella))
    assert resultados == [False, False, False]
    assert 0 < redis_controlable.ttl(f"recuperacion:bloqueo:{huella}") <= asignado - 49, "el bloqueo conserva lo que le quedaba"
    redis_controlable.avanzar(11)  # 61 s
    assert almacen.aceptar_solicitud(huella) is True


def test_cinco_por_hora_la_sexta_se_bloquea_y_pasada_la_hora_se_acepta(almacen, redis_controlable, huella):
    """RF-03.11: cinco aceptadas (0, 60, 120, 180, 240 s); la sexta (300 s) y la de 3 599 s, bloqueadas; la de 3 601 s, aceptada."""
    ahora, resultados = 0, []
    for instante in (0, 60, 120, 180, 240, 300, 3599, 3601):
        redis_controlable.avanzar(instante - ahora)
        ahora = instante
        resultados.append(almacen.aceptar_solicitud(huella))
    assert resultados == [True, True, True, True, True, False, False, True]


def test_las_bloqueadas_por_la_hora_no_cuentan_ni_alargan_la_ventana(almacen, redis_controlable, huella):
    """RF-03.11: la ventana de una hora parte de la primera aceptada; lo bloqueado ni suma al contador ni la reinicia."""
    contador = f"recuperacion:hora:{huella}"
    for instante in range(5):  # 0, 60, 120, 180 y 240 s
        redis_controlable.avanzar(60 if instante else 0)
        assert almacen.aceptar_solicitud(huella) is True
    restante = redis_controlable.ttl(contador)
    assert 3300 <= restante <= 3360
    redis_controlable.avanzar(60)
    assert almacen.aceptar_solicitud(huella) is False
    redis_controlable.avanzar(60)
    assert almacen.aceptar_solicitud(huella) is False
    assert redis_controlable.get(contador) == "5", "las bloqueadas se devuelven: el contador no pasa de 5"
    assert redis_controlable.ttl(contador) <= restante - 119, "la ventana siguió corriendo, no se reinició"


def test_una_bloqueada_por_la_hora_no_deja_el_bloqueo_de_60_s(almacen, redis_controlable, huella):
    """RF-03.10 / RF-03.11: lo que se rechaza por el límite horario no cuenta como solicitud para el minuto."""
    for instante in range(5):
        redis_controlable.avanzar(60 if instante else 0)
        assert almacen.aceptar_solicitud(huella) is True
    redis_controlable.avanzar(60)  # 300 s
    assert almacen.aceptar_solicitud(huella) is False
    assert redis_controlable.claves("recuperacion:bloqueo:*") == []


def test_una_bloqueada_por_el_minuto_no_suma_al_contador_por_hora(almacen, redis_controlable, huella):
    """RF-03.10 / RF-03.11: la bloqueada por el minuto no cuenta para las cinco de la hora."""
    assert almacen.aceptar_solicitud(huella) is True
    for _ in range(3):
        assert almacen.aceptar_solicitud(huella) is False
    assert redis_controlable.get(f"recuperacion:hora:{huella}") == "1"


def test_cada_correo_tiene_sus_propios_limites(almacen, redis_controlable, claves):
    """RF-03.10: el minuto de un correo no bloquea a otro correo distinto."""
    una = rc.huella_de_correo(claves.huella, "prueba.uno@prueba.invalid")
    otra = rc.huella_de_correo(claves.huella, "prueba.dos@prueba.invalid")
    assert almacen.aceptar_solicitud(una) is True
    assert almacen.aceptar_solicitud(otra) is True
    assert almacen.aceptar_solicitud(una) is False


def test_dos_solicitudes_simultaneas_aceptan_solo_una(almacen, redis_controlable, claves):
    """RF-03.10: aunque lleguen a la vez, el minuto lo toma una sola (se repite con 40 correos para dar tiempo a la carrera)."""
    for numero in range(40):
        huella = rc.huella_de_correo(claves.huella, f"prueba.carrera{numero}@prueba.invalid")
        resultados = _en_paralelo(2, lambda _: almacen.aceptar_solicitud(huella))
        assert sorted(resultados) == [False, True], f"ronda {numero}: {resultados}"
        assert redis_controlable.get(f"recuperacion:hora:{huella}") == "1"


def test_diez_solicitudes_simultaneas_aceptan_solo_una(almacen, redis_controlable, huella):
    """RF-03.10: con diez a la vez sigue siendo una sola, y el contador por hora cuenta una."""
    resultados = _en_paralelo(10, lambda _: almacen.aceptar_solicitud(huella))
    assert Counter(resultados) == {True: 1, False: 9}
    assert redis_controlable.get(f"recuperacion:hora:{huella}") == "1"


def test_las_claves_de_los_limites_llevan_la_huella_y_ningun_correo(almacen, redis_controlable, huella):
    """RF-03.12: bloqueo y contador por hora se identifican por la huella del correo normalizado, nunca por el correo."""
    almacen.aceptar_solicitud(huella)
    assert redis_controlable.claves("*") == [f"recuperacion:bloqueo:{huella}", f"recuperacion:hora:{huella}"]
    assert all(CORREO not in texto and "@" not in texto for texto in _volcado_del_servidor())
    assert 0 < redis_controlable.ttl(f"recuperacion:bloqueo:{huella}") <= 60
    assert 0 < redis_controlable.ttl(f"recuperacion:hora:{huella}") <= 3600


def test_con_el_contador_por_hora_perdido_la_siguiente_solicitud_se_acepta(almacen, redis_controlable, huella):
    """RF-03.25: si Redis pierde el contador, el límite se reinicia (se acepta de más, no se bloquea de más)."""
    for instante in range(5):
        redis_controlable.avanzar(60 if instante else 0)
        assert almacen.aceptar_solicitud(huella) is True
    redis_controlable.avanzar(60)
    assert almacen.aceptar_solicitud(huella) is False, "control: con el contador intacto, la sexta se bloquea"
    redis_controlable.perder(f"recuperacion:hora:{huella}")
    redis_controlable.avanzar(60)
    assert almacen.aceptar_solicitud(huella) is True


def test_con_el_bloqueo_de_un_minuto_perdido_la_siguiente_solicitud_se_acepta(almacen, redis_controlable, huella):
    """RF-03.25: si Redis pierde el bloqueo, la siguiente se acepta (y sigue contando para la hora)."""
    assert almacen.aceptar_solicitud(huella) is True
    redis_controlable.perder(f"recuperacion:bloqueo:{huella}")
    assert almacen.aceptar_solicitud(huella) is True
    assert redis_controlable.get(f"recuperacion:hora:{huella}") == "2"


# --- RF-03.7: la verificación del código ---------------------------------------------------------------------------

def test_leer_verificacion_devuelve_lo_guardado_sin_consumirlo(almacen, redis_controlable, huella):
    """RF-03.7: leer no gasta la verificación; «igual a la actual» deja reintentar con la misma."""
    almacen.guardar_verificacion(huella, "hash-del-secreto", CEDULA, VINCULO)
    for _ in range(2):
        leida = almacen.leer_verificacion(huella)
        assert (leida.hash_secreto, leida.cedula, leida.vinculo) == ("hash-del-secreto", CEDULA, VINCULO)
    assert redis_controlable.claves("*") == [f"recuperacion:verificacion:{huella}"]


@pytest.mark.parametrize("cedula", ["PRUEBA0001", "1-0234-0567", "PRUEBA|con|barras", ""])
def test_la_verificacion_conserva_la_cedula_tal_cual(almacen, redis_controlable, huella, cedula):
    """RF-03.7: la cédula se recupera igual aunque lleve el separador que usa el valor guardado."""
    almacen.guardar_verificacion(huella, "hash-del-secreto", cedula, VINCULO)
    leida = almacen.leer_verificacion(huella)
    assert (leida.hash_secreto, leida.cedula, leida.vinculo) == ("hash-del-secreto", cedula, VINCULO)


def test_leer_verificacion_sin_verificacion_devuelve_nada(almacen, redis_controlable, huella):
    """RF-03.7 / RF-03.25: sin clave (nunca existió, caducó o se perdió), no hay verificación."""
    assert almacen.leer_verificacion(huella) is None
    almacen.guardar_verificacion(huella, "hash-del-secreto", CEDULA, VINCULO)
    redis_controlable.perder(f"recuperacion:verificacion:{huella}")
    assert almacen.leer_verificacion(huella) is None


def test_guardar_otra_verificacion_reemplaza_a_la_anterior(almacen, redis_controlable, huella):
    """RF-03.7: una verificación nueva del mismo correo deja sin efecto la anterior y reinicia sus 10 minutos."""
    almacen.guardar_verificacion(huella, "hash-viejo", CEDULA, VINCULO)
    redis_controlable.avanzar(300)
    almacen.guardar_verificacion(huella, "hash-nuevo", CEDULA, VINCULO)
    assert almacen.leer_verificacion(huella).hash_secreto == "hash-nuevo"
    assert 599 <= redis_controlable.ttl(f"recuperacion:verificacion:{huella}") <= 600


def test_consumir_verificacion_solo_la_gasta_una_vez(almacen, redis_controlable, huella):
    """RF-03.7: el segundo `DEL` devuelve 0, así solo una petición cambia la contraseña con una verificación."""
    almacen.guardar_verificacion(huella, "hash-del-secreto", CEDULA, VINCULO)
    assert almacen.consumir_verificacion(huella) == 1
    assert almacen.consumir_verificacion(huella) == 0
    assert almacen.leer_verificacion(huella) is None
    assert redis_controlable.claves("*") == []


def test_dos_consumos_simultaneos_gastan_la_verificacion_una_sola_vez(almacen, redis_controlable, huella):
    """RF-03.7: con dos cambios de contraseña a la vez, solo uno obtiene el 1."""
    almacen.guardar_verificacion(huella, "hash-del-secreto", CEDULA, VINCULO)
    resultados = _en_paralelo(8, lambda _: almacen.consumir_verificacion(huella))
    assert sorted(resultados) == [0] * 7 + [1]


# --- RF-03.20: el almacén falla cerrado -----------------------------------------------------------------------------

OPERACIONES = {
    "guardar_estado": lambda almacen, huella: almacen.guardar_estado(huella, "hash", "emision", "cedula", "vinculo"),
    "registrar_intento": lambda almacen, huella: almacen.registrar_intento(huella),
    "aceptar_solicitud": lambda almacen, huella: almacen.aceptar_solicitud(huella),
    "guardar_verificacion": lambda almacen, huella: almacen.guardar_verificacion(huella, "hash", "cedula", "vinculo"),
    "leer_verificacion": lambda almacen, huella: almacen.leer_verificacion(huella),
    "consumir_verificacion": lambda almacen, huella: almacen.consumir_verificacion(huella),
}


@pytest.mark.parametrize("tipo, error_de_redis", [("conexion", ErrorDeConexion), ("tiempo", ErrorDeTiempo)])
@pytest.mark.parametrize("operacion", sorted(OPERACIONES))
def test_un_error_de_redis_se_convierte_en_almacen_no_disponible(almacen, redis_controlable, huella, operacion, tipo, error_de_redis):
    """RF-03.20: un error de conexión o de tiempo de `redis` sale como `AlmacenNoDisponible`, sin datos del correo."""
    redis_controlable.no_responde(tipo)
    with pytest.raises(almacen.AlmacenNoDisponible) as capturado:
        OPERACIONES[operacion](almacen, huella)
    assert isinstance(capturado.value.__cause__, error_de_redis)
    assert huella not in str(capturado.value)
    redis_controlable.responder_bien()
    assert redis_controlable.claves("*") == [], "un fallo no deja medio escrito el estado"


def test_un_error_de_red_del_sistema_tambien_es_almacen_no_disponible(almacen, redis_controlable, huella, monkeypatch):
    """RF-03.20: un fallo del sistema operativo al crear o usar el cliente (DNS, conexión rechazada) se traduce igual."""
    def sin_red():
        raise ConnectionRefusedError("sin red (simulado)")

    monkeypatch.setattr(almacen, "obtener_cliente", sin_red)
    for operacion in OPERACIONES.values():
        with pytest.raises(almacen.AlmacenNoDisponible):
            operacion(almacen, huella)


def test_un_error_que_no_es_de_redis_no_se_esconde(almacen, redis_controlable, huella, monkeypatch):
    """Un defecto del programa (no un fallo de Redis) debe verse como lo que es, no disfrazarse de servicio caído."""
    def defecto():
        raise ValueError("defecto simulado")

    monkeypatch.setattr(almacen, "obtener_cliente", defecto)
    with pytest.raises(ValueError):
        almacen.aceptar_solicitud(huella)


def test_almacen_no_disponible_no_es_un_error_de_redis(almacen):
    """RF-03.20: el servicio solo conoce `AlmacenNoDisponible`; no depende de la biblioteca `redis`."""
    assert issubclass(almacen.AlmacenNoDisponible, Exception)
    assert not issubclass(almacen.AlmacenNoDisponible, RedisError)


def test_tras_responder_bien_el_almacen_vuelve_a_funcionar(almacen, redis_controlable, huella):
    """RF-03.20: el reintento después de una caída se comporta con normalidad."""
    redis_controlable.no_responde("conexion")
    with pytest.raises(almacen.AlmacenNoDisponible):
        almacen.aceptar_solicitud(huella)
    redis_controlable.responder_bien()
    assert almacen.aceptar_solicitud(huella) is True


# --- RF-03.20: el cliente y su tiempo de espera ---------------------------------------------------------------------

def _espiar_from_url(monkeypatch):
    """Registra los argumentos con que se crea cada cliente con `redis.Redis.from_url` (sin cambiar lo que devuelve)."""
    llamadas = []
    original = redis.Redis.from_url

    def espia(cls, url, **kwargs):
        llamadas.append((url, kwargs))
        return original(url, **kwargs)

    monkeypatch.setattr(redis.Redis, "from_url", classmethod(espia))
    return llamadas


def test_el_cliente_se_crea_con_el_tiempo_de_espera_configurado(almacen, monkeypatch):
    """RF-03.20: `socket_timeout` y `socket_connect_timeout` valen `TIEMPO_ESPERA_REDIS`, y ese valor es menor de 30 s."""
    monkeypatch.setattr(almacen, "_cliente", None)
    llamadas = _espiar_from_url(monkeypatch)
    almacen.obtener_cliente()
    assert len(llamadas) == 1
    _, kwargs = llamadas[0]
    assert kwargs["socket_timeout"] == almacen.TIEMPO_ESPERA_REDIS
    assert kwargs["socket_connect_timeout"] == almacen.TIEMPO_ESPERA_REDIS
    assert 0 < almacen.TIEMPO_ESPERA_REDIS < 30, "menos que los 30 s que espera el navegador"
    assert almacen.TIEMPO_ESPERA_REDIS == 2.0


def test_el_cliente_usa_la_base_3_y_respuestas_en_texto(almacen, monkeypatch):
    """Plan §3.1: la recuperación vive en la base 3 (Celery usa la 0 y la 1; las conversaciones, la 2)."""
    monkeypatch.setattr(almacen, "_cliente", None)
    llamadas = _espiar_from_url(monkeypatch)
    cliente = almacen.obtener_cliente()
    url, kwargs = llamadas[0]
    assert url.endswith("/3")
    assert kwargs["decode_responses"] is True
    cliente.set("PRUEBA:base3", "1")
    assert redis.Redis(db=3, decode_responses=True).get("PRUEBA:base3") == "1"
    assert redis.Redis(db=0, decode_responses=True).get("PRUEBA:base3") is None


def test_el_cliente_se_crea_una_sola_vez(almacen, monkeypatch):
    """El cliente (y su conjunto de conexiones) se reutiliza entre llamadas, no se abre uno por solicitud."""
    monkeypatch.setattr(almacen, "_cliente", None)
    llamadas = _espiar_from_url(monkeypatch)
    assert almacen.obtener_cliente() is almacen.obtener_cliente()
    assert len(llamadas) == 1
