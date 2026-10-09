"""Pruebas de T6 (spec 003b): la verificación del código y el último paso de la recuperación de contraseña, por la API.

Cubren RF-03.5, RF-03.6, RF-03.7, RF-03.8 (pasos 2 y 3), RF-03.9 (por la API), RF-03.22 (pasos 2 y 3), RF-03.24 y RF-03.25
(por la API) y los mensajes de CU-04. Hablan con la API como lo haría el navegador (`cliente_api`, `correo_simulado`,
`iniciar_sesion`) y solo miran por dentro lo que el requisito pide mirar: el Redis simulado, para hacer caducar o perder el
estado (`redis_controlable`), y la base de pruebas, para comprobar que una contraseña no cambió.

Usan la base `servia_pruebas`, el correo simulado y el Redis simulado: nada sale de la prueba. Las cuentas son `PRUEBA`; las
contraseñas y los códigos inventados los genera la suite en cada corrida y el código real se lee del correo simulado y nunca se
imprime. Los mensajes de las aserciones traen solo códigos HTTP y los textos públicos de la API, nunca un token, un código ni una
contraseña. Ninguna espera es real: los plazos se hacen correr con `redis_controlable.avanzar`.
"""
import pytest
from sqlalchemy import text

from tests.soporte import datos, rastros
from tests.soporte import flujo_recuperacion as flujo

# Los textos de CU-04 y de la spec (la interfaz los muestra tal cual).
MENSAJE_VERIFICADO = "Código verificado correctamente"
MENSAJE_CAMBIADO = "Contraseña recuperada exitosamente"
MENSAJE_INCORRECTO = "Código de verificación incorrecto"
MENSAJE_CODIGO_VENCIDO = "El código ha expirado. Por favor, solicita un nuevo código de recuperación"
MENSAJE_PROCESO_VENCIDO = "El token de verificación ha expirado. Por favor, inicia el proceso de recuperación nuevamente"
MENSAJE_IGUAL_A_LA_ACTUAL = "La nueva contraseña debe ser diferente a la actual"
MENSAJE_INVALIDADO = (
    "Superaste el número de intentos permitidos. Solicita un nuevo código de recuperación. "
    "Si lo pediste hace menos de un minuto, espera un momento antes de volver a pedirlo."
)
MENSAJE_TOKEN_NO_RECONOCIDO = "Token inválido. El enlace de recuperación no es válido"
MENSAJE_CODIGO_DE_6_DIGITOS = "El código debe tener exactamente 6 dígitos"
MENSAJE_FALTAN_DATOS = "Token y nueva contraseña son requeridos"
MENSAJE_CONTRASENA_CORTA = "La nueva contraseña debe tener al menos 6 caracteres"

PATRON_ESTADO = "recuperacion:estado:*"
PATRON_VERIFICACION = "recuperacion:verificacion:*"
CADUCIDAD_ESTADO = 900  # 15 minutos (RF-03.4)
CADUCIDAD_VERIFICACION = 600  # 10 minutos (RF-03.7)


# --- Apoyo --------------------------------------------------------------------------------------------------------------

def _consultar(consulta, parametros):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros).fetchall()


def _hash_guardado(cedula):
    return _consultar("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": cedula})[0][0]


def _texto(respuesta):
    """El mensaje público de una respuesta (`message` si salió bien, `detail` si es un error), sin tokens."""
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return None
    return cuerpo.get("message", cuerpo.get("detail")) if isinstance(cuerpo, dict) else None


def _resultado(respuesta):
    """Lo que una prueba compara de una respuesta: su código HTTP y su mensaje público."""
    return respuesta.status_code, _texto(respuesta)


def _iniciar_sesion_con(cliente_api, correo, contrasena):
    return cliente_api.post("/auth/login", json={"email": correo, "password": str(contrasena)})


def _avanzar_hasta(redis_controlable, patron, caducidad_total, segundos):
    """Lleva la única clave de ese patrón a `segundos` de su creación, en tiempo virtual.

    `avanzar` suma al tiempo real que ya pasó (la caducidad de un Redis se mide con el reloj real), así que se descuenta ese
    tiempo: sin esto, «a los 14 min 59 s» dependería de cuánto tardó la prueba y podría fallar en una máquina lenta.
    """
    claves = redis_controlable.claves(patron)
    assert len(claves) == 1, f"se esperaba una clave para {patron} y hay {len(claves)}"
    transcurrido = caducidad_total - redis_controlable.pttl(claves[0]) / 1000
    redis_controlable.avanzar(segundos - transcurrido)


def _editar_como_administrador(cliente_api, cabeceras_del_administrador, cuenta, correo=None):
    """Edita la cuenta con `PUT /usuarios/{id}` como la pantalla de gestión: cambia solo el correo (y deja igual el resto)."""
    from app.db.database import SessionLocal
    from app.db.models import T_Usuario

    with SessionLocal() as db:
        fila = db.query(T_Usuario).filter(T_Usuario.CN_Id_usuario == cuenta.cedula).one()
        cuerpo = {
            "nombre_usuario": fila.CT_Nombre_usuario, "nombre": fila.CT_Nombre, "apellido_uno": fila.CT_Apellido_uno,
            "apellido_dos": fila.CT_Apellido_dos or "", "correo": correo or fila.CT_Correo, "id_rol": fila.CN_Id_rol,
            "id_estado": fila.CN_Id_estado,
        }
    respuesta = cliente_api.put(f"/usuarios/{cuenta.cedula}", json=cuerpo, headers=cabeceras_del_administrador)
    assert respuesta.status_code == 200, f"No se pudo editar la cuenta de prueba (código {respuesta.status_code})."


@pytest.fixture
def nueva_cuenta(registro_de_datos):
    """Una función que crea una cuenta `PRUEBA` más (Usuario Gubernamental, Activa) y la deja registrada para su limpieza."""

    def _crear():
        return datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)

    return _crear


@pytest.fixture
def cuenta_inactiva(cliente_api, iniciar_sesion, administrador, nueva_cuenta):
    """Una cuenta `PRUEBA` ya desactivada por el Administrador con `PUT /usuarios/{id}`, como lo hace la interfaz."""
    cuenta = nueva_cuenta()
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)
    return cuenta


@pytest.fixture
def proceso(cliente_api, correo_simulado, redis_controlable, nueva_cuenta):
    """Una función que pide el código de una cuenta Activa nueva y devuelve `(cuenta, token, código real)`."""

    def _pedir():
        cuenta = nueva_cuenta()
        respuesta = flujo.solicitar(cliente_api, cuenta.correo)
        assert respuesta.status_code == 200
        return cuenta, respuesta.json()["token"], flujo.codigo_enviado(correo_simulado)

    return _pedir


def _verificar_ok(cliente_api, token, codigo):
    """Verifica el código y devuelve el token de verificación; falla con el código HTTP si no se pudo."""
    respuesta = flujo.verificar(cliente_api, token, codigo)
    assert _resultado(respuesta) == (200, MENSAJE_VERIFICADO)
    return respuesta.json()["verificationToken"]


# --- El flujo completo (RF-03.4, RF-03.7, CU-04) -----------------------------------------------------------------------------

def test_el_flujo_completo_cambia_la_contrasena_y_solo_sirve_la_nueva(cliente_api, proceso):
    """RF-03.7: solicitar, verificar y cambiar; el inicio de sesión con la contraseña nueva funciona y con la anterior no."""
    cuenta, token, codigo = proceso()
    nueva = datos.generar_contrasena()

    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    cambio = flujo.cambiar(cliente_api, token_de_verificacion, nueva)

    assert _resultado(cambio) == (200, MENSAJE_CAMBIADO)
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, nueva).status_code == 200
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, cuenta.contrasena).status_code == 401


def test_tras_el_cambio_ni_la_verificacion_ni_el_codigo_vuelven_a_servir(cliente_api, proceso):
    """RF-03.7 y RF-03.24: la verificación se gasta una sola vez (un segundo cambio es un proceso vencido y no cambia nada) y
    el código usado deja de servir, porque la contraseña de la cuenta cambió."""
    cuenta, token, codigo = proceso()
    nueva, otra = datos.generar_contrasena(), datos.generar_contrasena()
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    assert flujo.cambiar(cliente_api, token_de_verificacion, nueva).status_code == 200

    repetido = flujo.cambiar(cliente_api, token_de_verificacion, otra)
    codigo_otra_vez = flujo.verificar(cliente_api, token, codigo)

    assert _resultado(repetido) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _resultado(codigo_otra_vez) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, nueva).status_code == 200
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, otra).status_code == 401


def test_si_otra_peticion_gasta_la_verificacion_antes_la_contrasena_no_cambia(cliente_api, monkeypatch, proceso):
    """RF-03.7: la verificación se gasta con un solo `DEL`; si otra petición la gastó entre la comprobación y el cambio
    (aquí se simula quitándola justo antes del `DEL`), la segunda recibe el proceso vencido y no guarda nada."""
    from app.repositories import recuperacion_estado_repository as almacen

    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    original = almacen.consumir_verificacion

    def _otra_peticion_llego_primero(huella):
        original(huella)
        return original(huella)  # el segundo DEL: ya no hay nada que gastar

    monkeypatch.setattr(almacen, "consumir_verificacion", _otra_peticion_llego_primero)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes


def test_con_la_huella_correcta_solo_el_secreto_de_la_verificacion_abre_el_cambio(cliente_api, proceso):
    """RF-03.7 y RF-03.21: quien conoce la huella (va en el token de la solicitud) no puede cambiar la contraseña con un secreto
    inventado ni con el token de la solicitud usado como si fuera el de verificación."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    huella = token_de_verificacion.split(".")[0]
    nueva = datos.generar_contrasena()

    con_secreto_inventado = flujo.cambiar(cliente_api, f"{huella}.{'Z' * 43}", nueva)
    con_el_token_de_la_solicitud = flujo.cambiar(cliente_api, token, nueva)

    assert _resultado(con_secreto_inventado) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _resultado(con_el_token_de_la_solicitud) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes
    assert _resultado(flujo.cambiar(cliente_api, token_de_verificacion, nueva)) == (200, MENSAJE_CAMBIADO)


# --- Caducidades (RF-03.7) -------------------------------------------------------------------------------------------------------

def test_el_codigo_sirve_a_los_14_min_59_s(cliente_api, redis_controlable, proceso):
    """RF-03.7: a los 14 minutos 59 segundos de emitido, el código correcto se acepta."""
    _, token, codigo = proceso()

    _avanzar_hasta(redis_controlable, PATRON_ESTADO, CADUCIDAD_ESTADO, 14 * 60 + 59)

    assert _resultado(flujo.verificar(cliente_api, token, codigo)) == (200, MENSAJE_VERIFICADO)


def test_el_codigo_ya_no_sirve_a_los_15_min_1_s_y_responde_codigo_vencido(cliente_api, redis_controlable, proceso):
    """RF-03.7 y CU-04: a los 15 minutos 1 segundo, ni el código correcto sirve y el mensaje es el del código vencido."""
    _, token, codigo = proceso()

    _avanzar_hasta(redis_controlable, PATRON_ESTADO, CADUCIDAD_ESTADO, 15 * 60 + 1)

    assert _resultado(flujo.verificar(cliente_api, token, codigo)) == (400, MENSAJE_CODIGO_VENCIDO)


def test_el_cambio_se_permite_a_los_9_min_59_s_de_la_verificacion(cliente_api, redis_controlable, proceso):
    """RF-03.7: a los 9 minutos 59 segundos de verificado el código, la contraseña se puede cambiar."""
    _, token, codigo = proceso()
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)

    _avanzar_hasta(redis_controlable, PATRON_VERIFICACION, CADUCIDAD_VERIFICACION, 9 * 60 + 59)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())
    assert _resultado(cambio) == (200, MENSAJE_CAMBIADO)


def test_el_cambio_ya_no_se_permite_a_los_10_min_1_s_y_responde_proceso_vencido(cliente_api, redis_controlable, proceso):
    """RF-03.7 y CU-04: a los 10 minutos 1 segundo de verificado el código, el cambio se rechaza y la contraseña no cambia."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)

    _avanzar_hasta(redis_controlable, PATRON_VERIFICACION, CADUCIDAD_VERIFICACION, 10 * 60 + 1)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())
    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes


# --- Los mensajes de CU-04 (RF-03.7) ---------------------------------------------------------------------------------------------

def test_un_codigo_incorrecto_responde_codigo_incorrecto_y_permite_reintentar(cliente_api, proceso):
    """RF-03.7 y CU-04 FE-01: el código incorrecto da el mensaje de CU-04 (400) y no impide usar después el correcto."""
    _, token, codigo = proceso()

    incorrecto = flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))
    correcto = flujo.verificar(cliente_api, token, codigo)

    assert _resultado(incorrecto) == (400, MENSAJE_INCORRECTO)
    assert _resultado(correcto) == (200, MENSAJE_VERIFICADO)


def test_igual_a_la_actual_se_rechaza_y_deja_reintentar_con_la_misma_verificacion(cliente_api, proceso):
    """RF-03.7 y CU-04: la contraseña igual a la actual se rechaza con su mensaje, no se guarda y la misma verificación sirve
    todavía para cambiarla por otra."""
    cuenta, token, codigo = proceso()
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    nueva = datos.generar_contrasena()

    igual = flujo.cambiar(cliente_api, token_de_verificacion, cuenta.contrasena)
    distinta = flujo.cambiar(cliente_api, token_de_verificacion, nueva)

    assert _resultado(igual) == (400, MENSAJE_IGUAL_A_LA_ACTUAL)
    assert _resultado(distinta) == (200, MENSAJE_CAMBIADO)
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, nueva).status_code == 200


# --- Entrada inválida (RF-03.9, RF-03.22) ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("codigo_invalido", ["123", "1234567", "12345a", "", " 123456", "١٢٣٤٥٦"])
def test_un_codigo_que_no_son_6_digitos_no_consume_intento(cliente_api, proceso, codigo_invalido):
    """RF-03.9 y RF-03.22: un código de 3 o 7 dígitos, con letras, vacío, con espacios o con dígitos no ASCII responde 400 con su
    mensaje y NO gasta intentos: después de diez así, cuatro incorrectos y el quinto correcto todavía se aceptan."""
    _, token, codigo = proceso()

    invalidos = [_resultado(flujo.verificar(cliente_api, token, codigo_invalido)) for _ in range(10)]
    incorrectos = [_resultado(flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))) for _ in range(4)]
    quinto = flujo.verificar(cliente_api, token, codigo)

    assert invalidos == [(400, MENSAJE_CODIGO_DE_6_DIGITOS)] * 10
    assert incorrectos == [(400, MENSAJE_INCORRECTO)] * 4
    assert _resultado(quinto) == (200, MENSAJE_VERIFICADO)


def test_la_entrada_invalida_del_ultimo_paso_responde_400_y_no_gasta_la_verificacion(cliente_api, proceso):
    """RF-03.22: sin datos, sin token o con una contraseña de menos de 6 caracteres el último paso responde 400 con su mensaje
    (nunca 422) y la verificación sigue vigente para cambiar la contraseña después."""
    _, token, codigo = proceso()
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)

    sin_datos = cliente_api.post(flujo.RUTA_CAMBIAR, json={})
    sin_token = flujo.cambiar(cliente_api, "", datos.generar_contrasena())
    sin_contrasena = flujo.cambiar(cliente_api, token_de_verificacion, "")
    corta = flujo.cambiar(cliente_api, token_de_verificacion, "12345")
    valida = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(sin_datos) == (400, MENSAJE_FALTAN_DATOS)
    assert _resultado(sin_token) == (400, MENSAJE_FALTAN_DATOS)
    assert _resultado(sin_contrasena) == (400, MENSAJE_FALTAN_DATOS)
    assert _resultado(corta) == (400, MENSAJE_CONTRASENA_CORTA)
    assert _resultado(valida) == (200, MENSAJE_CAMBIADO)


def test_sin_datos_la_verificacion_responde_400_y_no_422(cliente_api):
    """RF-03.22: un cuerpo vacío en la verificación responde 400 con el mensaje en español (FastAPI daría un 422 con una lista)."""
    respuesta = cliente_api.post(flujo.RUTA_VERIFICAR, json={})

    assert _resultado(respuesta) == (400, MENSAJE_CODIGO_DE_6_DIGITOS)


@pytest.mark.parametrize("token_raro", ["token-inventado", "x" * 45, "a.b", "A" * 22 + ".", "A" * 22 + "." + "B" * 30])
def test_un_token_con_otro_formato_responde_token_no_reconocido_sin_gastar_nada(cliente_api, redis_controlable, token_raro):
    """RF-03.22: un token que no tiene el formato de la recuperación responde 400 «Token inválido…» (en ambos pasos) y no deja
    ninguna clave en Redis."""
    paso_2 = flujo.verificar(cliente_api, token_raro, flujo.codigo_inventado())
    paso_3 = flujo.cambiar(cliente_api, token_raro, datos.generar_contrasena())

    assert _resultado(paso_2) == (400, MENSAJE_TOKEN_NO_RECONOCIDO)
    assert _resultado(paso_3) == (400, MENSAJE_PROCESO_VENCIDO)
    assert redis_controlable.claves() == []


def test_un_token_bien_formado_que_nadie_emitio_responde_codigo_vencido_y_no_deja_claves(cliente_api, redis_controlable):
    """RF-03.25 y RF-03.22: un token con el formato correcto pero sin estado (nadie lo emitió) se rechaza como un código vencido
    y contar el intento no deja ninguna clave sin caducidad en Redis."""
    inventado = "A" * 22 + "." + "B" * 22

    paso_2 = flujo.verificar(cliente_api, inventado, flujo.codigo_inventado())
    paso_3 = flujo.cambiar(cliente_api, inventado, datos.generar_contrasena())

    assert _resultado(paso_2) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _resultado(paso_3) == (400, MENSAJE_PROCESO_VENCIDO)
    assert redis_controlable.claves() == []


# --- Cinco intentos (RF-03.9) ------------------------------------------------------------------------------------------------------

def test_el_quinto_fallo_responde_429_con_el_mensaje_de_invalidacion_y_el_correcto_ya_no_sirve(cliente_api, proceso):
    """RF-03.9 y RF-03.22: cuatro códigos incorrectos dan 400; el quinto da 429 con el mensaje de invalidación; el código
    correcto enviado después se rechaza con el mismo 429 (y los siguientes también)."""
    _, token, codigo = proceso()

    primeros = [_resultado(flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))) for _ in range(4)]
    quinto = flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))
    correcto_despues = flujo.verificar(cliente_api, token, codigo)
    otro_incorrecto = flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))

    assert primeros == [(400, MENSAJE_INCORRECTO)] * 4
    assert _resultado(quinto) == (429, MENSAJE_INVALIDADO)
    assert _resultado(correcto_despues) == (429, MENSAJE_INVALIDADO)
    assert _resultado(otro_incorrecto) == (429, MENSAJE_INVALIDADO)


def test_el_quinto_intento_con_el_codigo_correcto_todavia_se_acepta(cliente_api, proceso):
    """RF-03.9: cuatro fallos y el quinto intento con el código correcto se aprueba (el límite es de cinco comprobaciones)."""
    _, token, codigo = proceso()

    for _ in range(4):
        flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo))

    assert _resultado(flujo.verificar(cliente_api, token, codigo)) == (200, MENSAJE_VERIFICADO)


# --- Más de una solicitud (RF-03.4, RF-03.10, RF-03.11) -----------------------------------------------------------------------------

def test_una_segunda_solicitud_aceptada_deja_vencido_el_primer_codigo(cliente_api, correo_simulado, redis_controlable, proceso):
    """RF-03.4: con dos solicitudes aceptadas (61 s entre ellas) hay un solo código vigente por correo: el primero responde
    «código vencido» y solo vale el segundo."""
    cuenta, token_1, codigo_1 = proceso()
    redis_controlable.avanzar(61)
    segunda = flujo.solicitar(cliente_api, cuenta.correo)
    token_2, codigo_2 = segunda.json()["token"], flujo.codigo_enviado(correo_simulado)
    assert len(correo_simulado.intentos) == 2 and token_1 != token_2

    primero = flujo.verificar(cliente_api, token_1, codigo_1)
    segundo = flujo.verificar(cliente_api, token_2, codigo_2)

    assert _resultado(primero) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _resultado(segundo) == (200, MENSAJE_VERIFICADO)


def test_si_la_segunda_solicitud_fue_bloqueada_por_el_minuto_el_primer_codigo_sigue_vigente(
    cliente_api, correo_simulado, proceso
):
    """RF-03.4 y RF-03.10: una segunda solicitud con menos de 60 s de diferencia no envía ni reemplaza nada: el primer código
    sigue valiendo y el token de la solicitud bloqueada se rechaza como vencido."""
    cuenta, token_1, codigo_1 = proceso()
    bloqueada = flujo.solicitar(cliente_api, cuenta.correo)
    assert bloqueada.status_code == 200 and len(correo_simulado.intentos) == 1

    del_bloqueo = flujo.verificar(cliente_api, bloqueada.json()["token"], codigo_1)
    primero = flujo.verificar(cliente_api, token_1, codigo_1)

    assert _resultado(del_bloqueo) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _resultado(primero) == (200, MENSAJE_VERIFICADO)


def test_si_la_sexta_solicitud_de_la_hora_fue_bloqueada_el_ultimo_codigo_sigue_vigente(
    cliente_api, correo_simulado, redis_controlable, proceso
):
    """RF-03.4 y RF-03.11: cinco solicitudes aceptadas (con 61 s entre ellas) y una sexta dentro de la hora, bloqueada por el
    límite: no sale otro correo y el código de la quinta sigue valiendo."""
    cuenta, token, codigo = proceso()
    for _ in range(4):
        redis_controlable.avanzar(61)
        respuesta = flujo.solicitar(cliente_api, cuenta.correo)
        token, codigo = respuesta.json()["token"], flujo.codigo_enviado(correo_simulado)
    assert len(correo_simulado.intentos) == 5
    redis_controlable.avanzar(61)

    sexta = flujo.solicitar(cliente_api, cuenta.correo)

    assert sexta.status_code == 200 and len(correo_simulado.intentos) == 5
    assert _resultado(flujo.verificar(cliente_api, token, codigo)) == (200, MENSAJE_VERIFICADO)


# --- Estado perdido (RF-03.25) -------------------------------------------------------------------------------------------------------

def test_con_el_estado_perdido_ni_el_codigo_correcto_sirve(cliente_api, redis_controlable, proceso):
    """RF-03.25: si Redis pierde el estado de la solicitud, el código correcto responde «El código ha expirado…» y no queda
    ninguna clave del estado (ni un contador huérfano)."""
    _, token, codigo = proceso()
    for clave in redis_controlable.claves(PATRON_ESTADO):
        redis_controlable.perder(clave)

    respuesta = flujo.verificar(cliente_api, token, codigo)

    assert _resultado(respuesta) == (400, MENSAJE_CODIGO_VENCIDO)
    assert redis_controlable.claves(PATRON_ESTADO) == []


def test_con_la_verificacion_perdida_el_cambio_responde_proceso_vencido(cliente_api, redis_controlable, proceso):
    """RF-03.25: si Redis pierde la verificación, el último paso responde el mensaje de proceso vencido y la contraseña no cambia."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    for clave in redis_controlable.claves(PATRON_VERIFICACION):
        redis_controlable.perder(clave)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes


def test_con_todo_el_redis_perdido_ningun_paso_acepta_nada(cliente_api, redis_controlable, proceso):
    """RF-03.25: si el servidor pierde todas sus claves (reinicio), el código correcto y el token de verificación se rechazan."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    redis_controlable.perder_todas()

    paso_2 = flujo.verificar(cliente_api, token, codigo)
    paso_3 = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(paso_2) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _resultado(paso_3) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes


# --- La cuenta cambia durante el proceso (RF-03.5, RF-03.6, RF-03.24) ---------------------------------------------------------------

def test_una_cuenta_desactivada_despues_de_verificar_responde_proceso_vencido_y_no_cambia(
    cliente_api, iniciar_sesion, administrador, proceso
):
    """RF-03.6 y RF-03.24 (c): solicitar, verificar, desactivar la cuenta como Administrador y cambiar: mismo mensaje y código
    que un proceso vencido, sin revelar el motivo; la contraseña no cambia y el inicio de sesión sigue rechazado."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)
    nueva = datos.generar_contrasena()

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, nueva)

    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, nueva).status_code == 401


def test_una_cuenta_desactivada_antes_de_verificar_responde_codigo_vencido(cliente_api, iniciar_sesion, administrador, proceso):
    """RF-03.6 y RF-03.24 (c): si la cuenta se desactiva después de pedir el código, el código correcto se rechaza como un
    código vencido (sin revelar el motivo) y no habilita ningún cambio."""
    cuenta, token, codigo = proceso()
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)

    respuesta = flujo.verificar(cliente_api, token, codigo)

    assert _resultado(respuesta) == (400, MENSAJE_CODIGO_VENCIDO)
    assert flujo.cambiar(cliente_api, token, datos.generar_contrasena()).status_code == 400


def test_si_el_administrador_restablece_la_contrasena_el_codigo_deja_de_servir(
    cliente_api, correo_simulado, iniciar_sesion, administrador, proceso
):
    """RF-03.24 (a): solicitar, restablecer la contraseña como Administrador (vía a) y verificar con el código correcto: se
    rechaza como código vencido y la contraseña temporal que dejó el Administrador no cambia (sigue sirviendo)."""
    cuenta, token, codigo = proceso()
    resultado = cliente_api.post(f"/usuarios/{cuenta.cedula}/resetear-contrasenna", headers=iniciar_sesion(administrador))
    assert resultado.status_code == 200
    temporal = rastros.valor_tras(correo_simulado.contenido_real().texto, "Tu nueva contraseña temporal es:")
    dejada_por_el_administrador = _hash_guardado(cuenta.cedula)

    verificacion = flujo.verificar(cliente_api, token, codigo)
    cambio = flujo.cambiar(cliente_api, token, datos.generar_contrasena())

    assert _resultado(verificacion) == (400, MENSAJE_CODIGO_VENCIDO)
    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == dejada_por_el_administrador
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, temporal).status_code == 200


def test_si_el_administrador_restablece_la_contrasena_despues_de_verificar_el_cambio_se_rechaza(
    cliente_api, correo_simulado, iniciar_sesion, administrador, proceso
):
    """RF-03.24 (a): si el Administrador restablece la contraseña entre la verificación y el último paso, el cambio responde
    proceso vencido y la contraseña temporal no cambia."""
    cuenta, token, codigo = proceso()
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    cliente_api.post(f"/usuarios/{cuenta.cedula}/resetear-contrasenna", headers=iniciar_sesion(administrador))
    temporal = rastros.valor_tras(correo_simulado.contenido_real().texto, "Tu nueva contraseña temporal es:")
    dejada_por_el_administrador = _hash_guardado(cuenta.cedula)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == dejada_por_el_administrador
    assert _iniciar_sesion_con(cliente_api, cuenta.correo, temporal).status_code == 200


def test_si_el_administrador_cambia_el_correo_el_cambio_responde_proceso_vencido_y_no_cambia(
    cliente_api, iniciar_sesion, administrador, proceso
):
    """RF-03.24 (b): solicitar y verificar, el Administrador cambia el correo de la cuenta y el último paso se rechaza como
    proceso vencido; la contraseña de la cuenta no cambia."""
    cuenta, token, codigo = proceso()
    antes = _hash_guardado(cuenta.cedula)
    token_de_verificacion = _verificar_ok(cliente_api, token, codigo)
    correo_nuevo = cuenta.correo.replace("@", ".nuevo@")
    _editar_como_administrador(cliente_api, iniciar_sesion(administrador), cuenta, correo=correo_nuevo)

    cambio = flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena())

    assert _resultado(cambio) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes
    assert _iniciar_sesion_con(cliente_api, correo_nuevo, cuenta.contrasena).status_code == 200


def test_si_el_administrador_cambia_el_correo_antes_de_verificar_el_codigo_se_rechaza(
    cliente_api, iniciar_sesion, administrador, proceso
):
    """RF-03.24 (b): si el correo cambia después de pedir el código, el código correcto se rechaza como código vencido."""
    cuenta, token, codigo = proceso()
    _editar_como_administrador(
        cliente_api, iniciar_sesion(administrador), cuenta, correo=cuenta.correo.replace("@", ".nuevo@")
    )

    respuesta = flujo.verificar(cliente_api, token, codigo)

    assert _resultado(respuesta) == (400, MENSAJE_CODIGO_VENCIDO)


def test_editar_otros_datos_de_la_cuenta_no_interrumpe_la_recuperacion(cliente_api, iniciar_sesion, administrador, proceso):
    """Control positivo de RF-03.24: una edición del Administrador que no toca el estado, el correo ni la contraseña (aquí, la
    misma ficha sin cambios) no vence el proceso; así los rechazos de arriba se deben al cambio y no a cualquier edición."""
    cuenta, token, codigo = proceso()
    _editar_como_administrador(cliente_api, iniciar_sesion(administrador), cuenta)

    assert _resultado(flujo.verificar(cliente_api, token, codigo)) == (200, MENSAJE_VERIFICADO)


def test_una_cuenta_inactiva_no_cambia_su_contrasena_por_ninguna_via_del_flujo(
    cliente_api, correo_simulado, cuenta_inactiva
):
    """RF-03.5 (b): pedir, verificar un código cualquiera y cambiar con la cuenta Inactiva: se rechaza igual que un proceso
    vencido, la contraseña no cambia, el inicio de sesión sigue rechazado y no salió ningún correo."""
    antes = _hash_guardado(cuenta_inactiva.cedula)
    nueva = datos.generar_contrasena()
    token = flujo.solicitar(cliente_api, cuenta_inactiva.correo).json()["token"]

    paso_2 = flujo.verificar(cliente_api, token, flujo.codigo_inventado())
    paso_3 = flujo.cambiar(cliente_api, token, nueva)

    assert correo_simulado.intentos == []
    assert _resultado(paso_2) == (400, MENSAJE_INCORRECTO)
    assert _resultado(paso_3) == (400, MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta_inactiva.cedula) == antes
    assert _iniciar_sesion_con(cliente_api, cuenta_inactiva.correo, nueva).status_code == 401


# --- Los pasos 2 y 3 no delatan qué cuentas existen (RF-03.8) --------------------------------------------------------------------------

def _tres_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva):
    """Hace la solicitud de una cuenta Activa, un correo sin cuenta y una cuenta Inactiva. Devuelve `{caso: (token, código real)}`."""
    activa = nueva_cuenta()
    casos = {}
    for nombre, correo in (("activa", activa.correo), ("no_registrada", flujo.correo_sin_cuenta()), ("inactiva", cuenta_inactiva.correo)):
        token = flujo.solicitar(cliente_api, correo).json()["token"]
        casos[nombre] = (token, flujo.codigo_enviado(correo_simulado) if nombre == "activa" else None)
    return casos


def test_los_pasos_2_y_3_dan_los_mismos_mensajes_y_codigos_hasta_el_429_para_los_tres_casos(
    cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva
):
    """RF-03.8: cuenta Activa (con un código incorrecto), correo no registrado y cuenta Inactiva responden igual en el paso 2
    (cuatro 400, el 429 del quinto fallo y los siguientes) y en el paso 3 con el token de la solicitud."""
    casos = _tres_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva)

    paso_2 = {
        nombre: [
            flujo.normalizar_para_comparar(flujo.verificar(cliente_api, token, flujo.codigo_inventado(real)))
            for _ in range(6)
        ]
        for nombre, (token, real) in casos.items()
    }
    paso_3 = {
        nombre: flujo.normalizar_para_comparar(flujo.cambiar(cliente_api, token, datos.generar_contrasena()))
        for nombre, (token, _) in casos.items()
    }

    assert [intento["estado"] for intento in paso_2["activa"]] == [400, 400, 400, 400, 429, 429]
    assert [intento["mensaje"] for intento in paso_2["activa"]] == [MENSAJE_INCORRECTO] * 4 + [MENSAJE_INVALIDADO] * 2
    assert paso_3["activa"]["estado"] == 400 and paso_3["activa"]["mensaje"] == MENSAJE_PROCESO_VENCIDO
    distintos = [
        (nombre, paso) for nombre in ("no_registrada", "inactiva")
        for paso, obtenido, esperado in (("paso_2", paso_2[nombre], paso_2["activa"]), ("paso_3", paso_3[nombre], paso_3["activa"]))
        if obtenido != esperado
    ]
    assert distintos == [], f"pasos que se distinguen de la cuenta Activa: {distintos}"


def test_los_tres_casos_caducan_igual_a_los_15_min_1_s(
    cliente_api, correo_simulado, redis_controlable, nueva_cuenta, cuenta_inactiva
):
    """RF-03.8: con la misma caducidad, a los 15 minutos 1 segundo los tres casos responden lo mismo en el paso 2 (aun con el
    código correcto de la cuenta Activa)."""
    casos = _tres_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva)
    redis_controlable.avanzar(15 * 60 + 1)

    respuestas = {
        nombre: flujo.normalizar_para_comparar(flujo.verificar(cliente_api, token, real or flujo.codigo_inventado()))
        for nombre, (token, real) in casos.items()
    }

    assert respuestas["activa"]["estado"] == 400 and respuestas["activa"]["mensaje"] == MENSAJE_CODIGO_VENCIDO
    assert respuestas["no_registrada"] == respuestas["activa"] and respuestas["inactiva"] == respuestas["activa"]


def test_la_entrada_invalida_responde_igual_en_los_tres_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva):
    """RF-03.8 y RF-03.22: un código de 3 dígitos o un token mal formado responden lo mismo con cualquier cuenta (se resuelven
    antes de mirar la cuenta)."""
    casos = _tres_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva)

    respuestas = {
        nombre: (
            flujo.normalizar_para_comparar(flujo.verificar(cliente_api, token, "123")),
            flujo.normalizar_para_comparar(flujo.cambiar(cliente_api, token, "abc")),
        )
        for nombre, (token, _) in casos.items()
    }

    assert respuestas["activa"][0]["mensaje"] == MENSAJE_CODIGO_DE_6_DIGITOS
    assert respuestas["activa"][1]["mensaje"] == MENSAJE_CONTRASENA_CORTA
    assert respuestas["no_registrada"] == respuestas["activa"] and respuestas["inactiva"] == respuestas["activa"]


# --- Los códigos HTTP de los pasos 2 y 3 (RF-03.22) ---------------------------------------------------------------------------------------

def test_los_pasos_2_y_3_responden_200_400_o_429_y_nunca_401_403_ni_404(cliente_api, redis_controlable, proceso):
    """RF-03.22: se recorre cada caso de los pasos 2 y 3 y se comprueba su código (§3.6 del plan): 200 al salir bien, 400 en la
    entrada inválida, el código incorrecto o vencido y el cambio rechazado, y 429 al invalidarse el código. Ninguno es 401, 403
    ni 404 (la interfaz cerraría la sesión con un 401)."""
    observados = []

    def _ver(esperado, respuesta):
        observados.append((esperado, respuesta.status_code))

    # Una cuenta que recorre el camino feliz con todas las entradas inválidas en medio.
    _, token, codigo = proceso()
    _ver(400, flujo.verificar(cliente_api, token, "123"))                           # código que no son 6 dígitos
    _ver(400, flujo.verificar(cliente_api, "", codigo))                              # sin token
    _ver(400, flujo.verificar(cliente_api, "token-inventado", codigo))               # token no reconocido
    _ver(400, flujo.verificar(cliente_api, "A" * 22 + "." + "B" * 22, codigo))       # token que nadie emitió
    _ver(400, flujo.verificar(cliente_api, token, flujo.codigo_inventado(codigo)))   # código incorrecto
    respuesta = flujo.verificar(cliente_api, token, codigo)
    _ver(200, respuesta)                                                              # código verificado
    token_de_verificacion = respuesta.json()["verificationToken"]
    _ver(400, flujo.cambiar(cliente_api, "", "abcdef"))                               # sin token
    _ver(400, flujo.cambiar(cliente_api, token_de_verificacion, "abc"))               # contraseña corta
    _ver(400, flujo.cambiar(cliente_api, "token-inventado", "abcdef"))                # token no reconocido
    _ver(400, flujo.cambiar(cliente_api, "A" * 22 + "." + "B" * 43, "abcdef"))        # verificación que nadie emitió
    _ver(200, flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena()))   # contraseña cambiada
    _ver(400, flujo.cambiar(cliente_api, token_de_verificacion, datos.generar_contrasena()))   # verificación ya gastada

    # Otra cuenta: la contraseña igual a la actual y el código invalidado por intentos.
    cuenta_2, token_2, codigo_2 = proceso()
    token_de_verificacion_2 = _verificar_ok(cliente_api, token_2, codigo_2)
    _ver(400, flujo.cambiar(cliente_api, token_de_verificacion_2, cuenta_2.contrasena))   # igual a la actual

    _, token_3, codigo_3 = proceso()
    for _ in range(4):
        _ver(400, flujo.verificar(cliente_api, token_3, flujo.codigo_inventado(codigo_3)))
    _ver(429, flujo.verificar(cliente_api, token_3, flujo.codigo_inventado(codigo_3)))     # quinto fallo: invalidado
    _ver(429, flujo.verificar(cliente_api, token_3, codigo_3))                              # el correcto ya no sirve

    # Otra cuenta: el código y la verificación vencen.
    _, token_4, codigo_4 = proceso()
    token_de_verificacion_4 = _verificar_ok(cliente_api, token_4, codigo_4)
    redis_controlable.avanzar(15 * 60 + 1)
    _ver(400, flujo.verificar(cliente_api, token_4, codigo_4))                              # código vencido
    _ver(400, flujo.cambiar(cliente_api, token_de_verificacion_4, "abcdef"))                # proceso vencido

    distintos = [(esperado, obtenido) for esperado, obtenido in observados if esperado != obtenido]
    assert distintos == []
    assert not [obtenido for _, obtenido in observados if obtenido in (401, 403, 404)]
    assert {obtenido for _, obtenido in observados} == {200, 400, 429}
