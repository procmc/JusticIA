"""Pruebas de T3 (spec 003b): la regresión de la recuperación pública de contraseña contra el código heredado.

Son las nueve regresiones del criterio de finalización de la spec. Se escribieron y se ejecutaron ANTES de tocar el código
heredado (rojo previo) y siguen la spec, no el comportamiento actual: cada una que el código heredado no cumple está marcada
como fallo esperado (`xfail`, estricto) con el requisito y la tarea que la corrige. Cuando esa tarea corrige el código, quita
la marca; un `XPASS` hace fallar la corrida, así ninguna se olvida.

Hablan solo con la API (`cliente_api`, `correo_simulado`, `iniciar_sesion`), como lo haría el navegador, y no dependen de la
forma interna del estado: ni de un token firmado ni de Redis. Lo único que leen por dentro es la base de pruebas, para
comprobar que una contraseña no cambió y qué filas dejó la bitácora.

Usan la base `servia_pruebas` y el correo simulado: ningún correo sale de la prueba. Las cuentas son `PRUEBA`; sus
contraseñas y los códigos inventados los genera la suite en cada corrida; el código real se lee del correo simulado y nunca
se imprime. Todo correo de prueba sin cuenta lleva «prueba» en su texto para que la limpieza por texto borre sus filas de
bitácora.
"""
import json

import pytest
from sqlalchemy import text

from tests.soporte import datos, rastros
from tests.soporte import flujo_recuperacion as flujo

MENSAJE_DEL_ERS = "Si el correo existe en nuestro sistema, recibirás un email con las instrucciones"
MENSAJE_PROCESO_VENCIDO = "El token de verificación ha expirado"
TIPO_RECUPERACION = 6  # TiposAccion.RECUPERACION_CONTRASENA
CASOS = ("activa", "limite", "no_registrada", "inactiva", "envio_fallido")


def _consultar(consulta, parametros):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros).fetchall()


def _hash_guardado(cedula):
    return _consultar("SELECT CT_Contrasenna FROM T_Usuario WHERE CN_Id_usuario = :c", {"c": cedula})[0][0]


def _texto_del_registro(texto, informacion_adicional):
    """El texto de una fila de bitácora junto con los valores de su información adicional, en minúsculas.

    Así la prueba busca el resultado de un paso sin depender del nombre del campo donde el sistema lo escribe.
    """
    partes = [texto or ""]
    try:
        adicional = json.loads(informacion_adicional) if informacion_adicional else {}
    except ValueError:
        adicional = {}
    if isinstance(adicional, dict):
        partes += [str(valor) for valor in adicional.values()]
    return " ".join(partes).lower()


def _pertenece(texto, informacion_adicional, id_usuario, correo, cedula):
    """Si una fila de bitácora es de la cuenta: lleva su usuario o nombra su correo (las filas sin usuario nombran el correo)."""
    if cedula is not None and id_usuario == cedula:
        return True
    return correo.lower() in _texto_del_registro(texto, informacion_adicional)


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


class _Caso:
    """La respuesta de la solicitud de un caso y los datos de la cuenta a la que se pidió (la cédula es `None` sin cuenta)."""

    def __init__(self, respuesta, correo, cedula):
        self.respuesta, self.correo, self.cedula = respuesta, correo, cedula


@pytest.fixture
def cinco_casos(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva):
    """Hace la solicitud de los cinco casos de RF-03.2 y devuelve un diccionario `caso -> _Caso`.

    - `activa`: una cuenta Activa. `limite`: la MISMA cuenta pedida otra vez enseguida (el límite de un código por minuto).
    - `no_registrada`: un correo sin cuenta. `inactiva`: una cuenta desactivada.
    - `envio_fallido`: otra cuenta Activa con el servidor de correo caído (el correo simulado falla); luego se restablece.
    Cada caso usa un correo distinto salvo `limite`, para que los límites de uno no afecten a otro.
    """
    activa, con_envio_fallido, sin_cuenta = nueva_cuenta(), nueva_cuenta(), flujo.correo_sin_cuenta()
    casos = {}
    casos["activa"] = _Caso(flujo.solicitar(cliente_api, activa.correo), activa.correo, activa.cedula)
    casos["limite"] = _Caso(flujo.solicitar(cliente_api, activa.correo), activa.correo, activa.cedula)
    casos["no_registrada"] = _Caso(flujo.solicitar(cliente_api, sin_cuenta), sin_cuenta, None)
    casos["inactiva"] = _Caso(
        flujo.solicitar(cliente_api, cuenta_inactiva.correo), cuenta_inactiva.correo, cuenta_inactiva.cedula
    )
    correo_simulado.fallar()
    casos["envio_fallido"] = _Caso(
        flujo.solicitar(cliente_api, con_envio_fallido.correo), con_envio_fallido.correo, con_envio_fallido.cedula
    )
    correo_simulado.responder_bien()
    return casos


# --- (1) RF-03.1 (a): el código solo viaja por el correo ---------------------------------------------------------------

def test_el_codigo_del_correo_no_viaja_en_la_respuesta_de_la_solicitud(cliente_api, correo_simulado, nueva_cuenta):
    """RF-03.1 (a): el código que llegó por correo no aparece en el cuerpo, en los encabezados ni en el token (decodificado
    en base64). Control positivo: sí está en el correo, así que la búsqueda no es en vacío."""
    cuenta = nueva_cuenta()

    respuesta = flujo.solicitar(cliente_api, cuenta.correo)

    assert respuesta.status_code == 200
    codigo = flujo.codigo_enviado(correo_simulado)
    donde = rastros.encontrar_en_rastros(
        codigo,
        correo=correo_simulado.contenido_real().texto,
        cuerpo=respuesta.text,
        encabezados=dict(respuesta.headers),
        token_decodificado=flujo.decodificar_token(respuesta.json().get("token")),
    )
    assert donde == ["correo"]


# --- (2) RF-03.2: la respuesta uniforme en los cinco casos ---------------------------------------------------------------

def test_los_cinco_casos_de_la_solicitud_responden_igual_en_forma_codigo_y_mensaje(cinco_casos):
    """RF-03.2: cuenta Activa, correo no registrado, cuenta Inactiva, envío fallido y límite alcanzado responden 200 con los
    mismos campos en el mismo orden, el mismo mensaje (el del ERS) y un token de la misma forma."""
    formas = {nombre: flujo.normalizar_para_comparar(cinco_casos[nombre].respuesta) for nombre in CASOS}

    assert formas["activa"]["estado"] == 200
    assert formas["activa"]["mensaje"] == MENSAJE_DEL_ERS
    distintos = [nombre for nombre in CASOS if formas[nombre] != formas["activa"]]
    assert distintos == [], f"casos que se distinguen de la cuenta Activa: {distintos}"


# --- (3) RF-03.5: una cuenta Inactiva ----------------------------------------------------------------------------------

def test_la_cuenta_inactiva_no_recibe_correo(cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva):
    """RF-03.5: pedir la recuperación de una cuenta Inactiva no envía ningún correo. Control positivo: una cuenta Activa
    pedida antes sí recibe uno (el correo simulado funciona), y tras pedir la Inactiva no hay ninguno más."""
    activa = nueva_cuenta()
    assert flujo.solicitar(cliente_api, activa.correo).status_code == 200
    assert [intento["a"] for intento in correo_simulado.intentos] == [activa.correo]

    respuesta = flujo.solicitar(cliente_api, cuenta_inactiva.correo)

    assert respuesta.status_code == 200
    assert [intento["a"] for intento in correo_simulado.intentos] == [activa.correo]


def test_la_cuenta_inactiva_no_puede_cambiar_su_contrasena_por_recuperacion(cliente_api, correo_simulado, cuenta_inactiva, nueva_cuenta):
    """RF-03.5: pedir, verificar y cambiar con una cuenta Inactiva no modifica su contraseña; el inicio de sesión sigue
    rechazado y la cuenta sigue Inactiva. Si el sistema envió un código (no debería), la prueba lo usa; si no, inventa uno.

    Control positivo (agregado en T5): una cuenta Activa SÍ verifica su código. Sin él, esta prueba pasaría en vacío en cuanto
    la solicitud dejara de enviar el código a la cuenta Inactiva, porque el último paso heredado rechaza cualquier token nuevo.
    """
    antes = _hash_guardado(cuenta_inactiva.cedula)
    nueva = datos.generar_contrasena()

    solicitud = flujo.solicitar(cliente_api, cuenta_inactiva.correo)
    token = solicitud.json().get("token")
    codigo = flujo.codigo_enviado(correo_simulado) if correo_simulado.intentos else flujo.codigo_inventado()
    verificacion = flujo.verificar(cliente_api, token, codigo)
    token_de_verificacion = verificacion.json().get("verificationToken") if verificacion.status_code == 200 else None
    cambio = flujo.cambiar(cliente_api, token_de_verificacion, nueva)

    assert cambio.status_code != 200
    assert _hash_guardado(cuenta_inactiva.cedula) == antes
    assert cliente_api.post(
        "/auth/login", json={"email": cuenta_inactiva.correo, "password": str(nueva)}
    ).status_code == 401
    assert _consultar(
        "SELECT e.CT_Nombre_estado FROM T_Usuario u JOIN T_Estado e ON e.CN_Id_estado = u.CN_Id_estado "
        "WHERE u.CN_Id_usuario = :c", {"c": cuenta_inactiva.cedula},
    )[0][0] == "Inactivo"

    activa = nueva_cuenta()
    token_de_la_activa = flujo.solicitar(cliente_api, activa.correo).json().get("token")
    assert flujo.verificar(cliente_api, token_de_la_activa, flujo.codigo_enviado(correo_simulado)).status_code == 200


# --- (4) RF-03.6: la cuenta se desactiva durante el proceso -------------------------------------------------------------

def test_una_cuenta_desactivada_despues_de_verificar_no_cambia_su_contrasena(
    cliente_api, iniciar_sesion, correo_simulado, administrador, nueva_cuenta
):
    """RF-03.6: solicitar, verificar, desactivar la cuenta como Administrador y cambiar: el último paso se rechaza como un
    proceso vencido (400, mensaje de CU-04) y la contraseña guardada no cambia."""
    cuenta = nueva_cuenta()
    antes = _hash_guardado(cuenta.cedula)
    token = flujo.solicitar(cliente_api, cuenta.correo).json().get("token")
    verificacion = flujo.verificar(cliente_api, token, flujo.codigo_enviado(correo_simulado))
    assert verificacion.status_code == 200
    flujo.desactivar_cuenta(cliente_api, iniciar_sesion(administrador), cuenta)

    cambio = flujo.cambiar(cliente_api, verificacion.json().get("verificationToken"), datos.generar_contrasena())

    assert cambio.status_code == 400
    assert cambio.json()["detail"].startswith(MENSAJE_PROCESO_VENCIDO)
    assert _hash_guardado(cuenta.cedula) == antes


# --- (5) RF-03.8: los pasos 2 y 3 no delatan qué cuentas existen -----------------------------------------------------------

def test_los_pasos_2_y_3_responden_igual_para_cuenta_activa_correo_no_registrado_y_cuenta_inactiva(
    cliente_api, correo_simulado, nueva_cuenta, cuenta_inactiva
):
    """RF-03.8: con una solicitud de cada caso, cinco códigos incorrectos seguidos dan la misma secuencia de códigos HTTP y
    mensajes (hasta el de invalidación del quinto fallo), y el último paso con el token de la solicitud también responde igual."""
    correos = {"activa": nueva_cuenta().correo, "no_registrada": flujo.correo_sin_cuenta(), "inactiva": cuenta_inactiva.correo}
    resultados = {}
    for caso, correo in correos.items():
        token = flujo.solicitar(cliente_api, correo).json().get("token")
        real = flujo.codigo_enviado(correo_simulado) if caso == "activa" else None
        resultados[caso] = {
            "paso_2": [
                flujo.normalizar_para_comparar(flujo.verificar(cliente_api, token, flujo.codigo_inventado(real)))
                for _ in range(5)
            ],
            "paso_3": flujo.normalizar_para_comparar(flujo.cambiar(cliente_api, token, datos.generar_contrasena())),
        }

    distintos = {
        caso: [paso for paso in ("paso_2", "paso_3") if resultados[caso][paso] != resultados["activa"][paso]]
        for caso in ("no_registrada", "inactiva")
    }
    assert distintos == {"no_registrada": [], "inactiva": []}, f"pasos que se distinguen de la cuenta Activa: {distintos}"
    # Control positivo (agregado en T5): la cuenta Activa recorre de verdad la verificación (cuatro códigos incorrectos y el
    # quinto invalida). Sin él, esta prueba pasaría en vacío en cuanto la solicitud emitiera tokens nuevos, porque el paso 2
    # heredado rechaza cualquier token nuevo igual para los tres casos.
    assert [intento["estado"] for intento in resultados["activa"]["paso_2"]] == [400, 400, 400, 400, 429]


# --- (6) RF-03.21: el token de la solicitud --------------------------------------------------------------------------------

def test_el_token_existe_con_la_misma_forma_en_los_cinco_casos_y_no_identifica_la_cuenta(cinco_casos):
    """RF-03.21: la solicitud devuelve siempre un token, con el mismo largo y el mismo conjunto de caracteres, y ni él ni lo
    que sale de decodificarlo en base64 contiene la cédula ni el correo (ni su parte local)."""
    tokens = {nombre: cinco_casos[nombre].respuesta.json().get("token") for nombre in CASOS}
    sin_token = [nombre for nombre, token in tokens.items() if not isinstance(token, str) or not token]
    formas = {nombre: flujo.forma_del_token(token) for nombre, token in tokens.items()}
    forma_distinta = [nombre for nombre in CASOS if formas[nombre] != formas["activa"]]
    revelan = []
    for nombre in CASOS:
        caso = cinco_casos[nombre]
        datos_de_la_cuenta = [caso.correo, caso.correo.split("@")[0]] + ([caso.cedula] if caso.cedula else [])
        if any(
            rastros.encontrar_en_rastros(
                dato, token=tokens[nombre] or "-", token_decodificado=flujo.decodificar_token(tokens[nombre])
            )
            for dato in datos_de_la_cuenta
        ):
            revelan.append(nombre)

    assert (sin_token, forma_distinta, revelan) == ([], [], []), (
        f"casos sin token: {sin_token}; con otra forma que la Activa: {forma_distinta}; "
        f"con datos de la cuenta en el token: {revelan}"
    )


# --- (7) RF-03.22: ningún error de la recuperación es 401 ni 403 ni 404 --------------------------------------------------------

def test_un_codigo_incorrecto_no_responde_401_ni_403_ni_404(cliente_api, correo_simulado, nueva_cuenta):
    """RF-03.22: un código incorrecto responde un 4xx distinto de 401, 403 y 404 (la interfaz cerraría la sesión con un 401).
    Control positivo: el código correcto sí lo acepta (200)."""
    cuenta = nueva_cuenta()
    token = flujo.solicitar(cliente_api, cuenta.correo).json().get("token")
    real = flujo.codigo_enviado(correo_simulado)

    incorrecto = flujo.verificar(cliente_api, token, flujo.codigo_inventado(real))
    correcto = flujo.verificar(cliente_api, token, real)

    assert 400 <= incorrecto.status_code < 500
    assert incorrecto.status_code not in (401, 403, 404)
    assert correcto.status_code == 200


# --- (8) RF-21.2: una fila de bitácora por paso -----------------------------------------------------------------------------------

def test_el_flujo_completo_deja_una_fila_de_bitacora_por_paso_en_orden_y_con_su_resultado(
    cliente_api, correo_simulado, nueva_cuenta
):
    """RF-21.2: solicitar, verificar y cambiar dejan tres filas del tipo «Recuperación de Contraseña», en ese orden, y cada
    una dice su resultado (código enviado, código verificado, contraseña cambiada)."""
    cuenta = nueva_cuenta()
    token = flujo.solicitar(cliente_api, cuenta.correo).json().get("token")
    verificacion = flujo.verificar(cliente_api, token, flujo.codigo_enviado(correo_simulado))
    assert verificacion.status_code == 200
    cambio = flujo.cambiar(cliente_api, verificacion.json().get("verificationToken"), datos.generar_contrasena())
    assert cambio.status_code == 200

    filas = _consultar(
        "SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_tipo_accion = :t "
        "AND (CN_Id_usuario = :c OR CT_Texto LIKE :m OR CT_Informacion_adicional LIKE :m) ORDER BY CN_Id_bitacora",
        {"t": TIPO_RECUPERACION, "c": cuenta.cedula, "m": f"%{cuenta.correo}%"},
    )

    assert len(filas) == 3
    resultados = ["código enviado", "código verificado", "contraseña cambiada"]
    for fila, resultado in zip(filas, resultados):
        assert resultado in _texto_del_registro(fila[0], fila[1])


# --- (9) RF-21.3: la consulta por tipo de acción ------------------------------------------------------------------------------------

def test_la_consulta_por_tipo_de_accion_devuelve_las_filas_de_recuperacion_con_su_resultado_tambien_las_sin_usuario(
    cliente_api, iniciar_sesion, correo_simulado, administrador, nueva_cuenta
):
    """RF-21.3: `GET /bitacora/registros?tipoAccion=6` como Administrador devuelve la fila de una solicitud sin cuenta (sin
    usuario) y la de una cuenta Activa, y cada una trae su resultado (correo no registrado, código enviado)."""
    cuenta, sin_cuenta = nueva_cuenta(), flujo.correo_sin_cuenta()
    flujo.solicitar(cliente_api, cuenta.correo)
    flujo.solicitar(cliente_api, sin_cuenta)

    respuesta = cliente_api.get(
        "/bitacora/registros", params={"tipoAccion": TIPO_RECUPERACION, "limite": 100}, headers=iniciar_sesion(administrador)
    )

    assert respuesta.status_code == 200
    items = respuesta.json()["items"]
    assert items and all(item["idTipoAccion"] == TIPO_RECUPERACION for item in items)
    de_sin_cuenta = [
        i for i in items if _pertenece(i["texto"], i["informacionAdicional"], i["idUsuario"], sin_cuenta, None)
    ]
    de_la_cuenta = [
        i for i in items if _pertenece(i["texto"], i["informacionAdicional"], i["idUsuario"], cuenta.correo, cuenta.cedula)
    ]
    assert len(de_sin_cuenta) == 1 and de_sin_cuenta[0]["idUsuario"] is None
    assert len(de_la_cuenta) == 1
    assert "correo no registrado" in _texto_del_registro(de_sin_cuenta[0]["texto"], de_sin_cuenta[0]["informacionAdicional"])
    assert "código enviado" in _texto_del_registro(de_la_cuenta[0]["texto"], de_la_cuenta[0]["informacionAdicional"])


# --- T5 (spec 003b): la solicitud nueva por la API real, contra SQL Server --------------------------------------------------------
# Estas dos pruebas no son regresiones del código heredado (no llevan marca de fallo esperado): comprueban con la consulta real a la
# base lo que las unitarias de `test_recuperacion_solicitud.py` solo pueden comprobar con un repositorio simulado.

def test_las_mayusculas_y_los_espacios_encuentran_la_cuenta_por_la_api(cliente_api, correo_simulado, nueva_cuenta):
    """RF-03.4 y RF-03.12: un correo con mayúsculas y espacios alrededor es el mismo que el de la cuenta (la consulta real a
    la base lo encuentra) y el único correo del código sale a la dirección de la cuenta."""
    cuenta = nueva_cuenta()

    respuesta = flujo.solicitar(cliente_api, f"  {cuenta.correo.upper()} ")

    assert respuesta.status_code == 200
    assert [intento["a"].lower() for intento in correo_simulado.intentos] == [cuenta.correo.lower()]


def test_un_correo_mal_formado_da_400_con_su_mensaje_y_no_crea_ninguna_clave(cliente_api, correo_simulado, redis_controlable):
    """RF-03.12 y RF-03.22: correo vacío, ausente o mal formado: 400 con el mensaje en español, sin correo y sin ninguna clave en
    Redis (no cuenta para los límites)."""
    for cuerpo in ({"email": ""}, {"email": "sin-arroba"}, {"email": "a" * 101 + "@prueba.invalid"}, {}):
        respuesta = cliente_api.post(flujo.RUTA_SOLICITAR, json=cuerpo)
        assert respuesta.status_code == 400, cuerpo
        assert respuesta.json() == {"detail": "Ingresa un correo electrónico válido"}

    assert correo_simulado.intentos == []
    assert redis_controlable.claves() == []


def test_una_cuenta_con_el_correo_guardado_en_mayusculas_se_encuentra_con_el_correo_normalizado(cliente_api, correo_simulado, nueva_cuenta):
    """RF-03.4 y RF-03.12: el servicio busca con el correo en minúsculas; la consulta real a la base lo encuentra aunque la
    cuenta lo tenga guardado en mayúsculas (la comparación no distingue mayúsculas, como en el código heredado)."""
    from app.db.database import engine

    cuenta = nueva_cuenta()
    with engine.begin() as conexion:
        conexion.execute(
            text("UPDATE T_Usuario SET CT_Correo = UPPER(CT_Correo) WHERE CN_Id_usuario = :c"), {"c": cuenta.cedula}
        )

    respuesta = flujo.solicitar(cliente_api, cuenta.correo.lower())

    assert respuesta.status_code == 200
    assert [intento["a"].lower() for intento in correo_simulado.intentos] == [cuenta.correo.lower()]
