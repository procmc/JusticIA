"""Pruebas humo de la integración (spec 002, T9; RA-02.6 y RA-02.7, con RNF-07).

Demuestran que la infraestructura de integración funciona de punta a punta; no cubren el requisito de ningún módulo:

- RNF-07: la API rechaza con 401 una petición sin token y con un token inválido: falso, firmado con otra clave o vencido
  (con un control: el mismo tipo de token, vigente y firmado por el sistema, sí pasa).
- RA-02.6 (c): un fragmento de texto inventado se guarda y se recupera en la colección de pruebas con el modelo de
  embeddings real y el filtro `metadata.numero_expediente` (la clave anidada que usa LangChain); y con dos fragmentos de
  asuntos distintos, la búsqueda semántica pone primero el afín a la consulta (solo el orden relativo, no los puntajes).
- RA-02.7: el flujo completo con los dos roles (inicio de sesión, acceso por rol, notebook, bitácora, tema, documento y
  fragmento) deja la base, Qdrant y la carpeta temporal en cero con la rutina `limpiar`. Lo que esa prueba demuestra es que
  `limpiar` funciona; la limpieza automática al terminar CADA prueba la cubren `tests/infraestructura/test_residuos.py`
  (con una corrida hija) y el conteo de residuos con el que falla el cierre de la sesión.

De RF-21 (bitácora) se verifica aquí SOLO lo del Administrador: que el inicio de sesión y la consulta de usuarios dejan
registros en `T_Bitacora`. NO se verifica que crear un notebook se registre: hoy `routes/notebooks.py` no lo registra,
un incumplimiento heredado que corresponde a la futura spec de notebooks (por eso la prueba no lo afirma).

Solo usan la base y la colección `servia_pruebas`, con datos inventados. Las contraseñas las genera la suite y no salen;
los JWT inventados se firman con una clave inventada que no es la del sistema, y los vencidos los firma el propio código
del sistema (`create_token`), de modo que la prueba nunca lee ni muestra el secreto.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import text

from tests.soporte import datos
from tests.soporte.nombres import NOMBRE_PRUEBAS, PREFIJO_DATOS

DIMENSION = 1024  # multilingual-e5-large

TEXTO_INVENTADO = (
    f"{PREFIJO_DATOS}: informe inventado sobre la renovación de licencias de pesca en un lago imaginario. "
    "Los pescadores ficticios presentan su solicitud en la ventanilla de la municipalidad inexistente."
)

# Un asunto claramente distinto del anterior, para comprobar que la búsqueda ordena por relevancia.
TEXTO_OTRO_ASUNTO = (
    f"{PREFIJO_DATOS}: manual inventado de mantenimiento de las turbinas de una central eólica imaginaria. "
    "El técnico ficticio revisa los rodamientos y lubrica el engranaje principal cada seis meses."
)

# Clave inventada con la que se firman los JWT «de otra clave». No es la del sistema (que la prueba nunca lee).
CLAVE_AJENA = "PRUEBA-clave-inventada-que-no-es-la-del-sistema-0123456789"

# (método, ruta, rol que exige) de endpoints que exigen sesión; el rol es el del Administrador o el del Usuario Gubernamental
# (en el código heredado, «Usuario Judicial»).
RUTAS_PROTEGIDAS = [
    pytest.param("GET", "/usuarios/", "Administrador", id="usuarios-admin"),
    pytest.param("GET", "/bitacora/registros", "Administrador", id="bitacora-admin"),
    pytest.param("GET", "/notebooks", "Usuario Judicial", id="notebooks-listar-gubernamental"),
    pytest.param("POST", "/notebooks", "Usuario Judicial", id="notebooks-crear-gubernamental"),
    pytest.param("GET", "/bitacora/mi-historial", "Usuario Judicial", id="historial-gubernamental"),
]


def _pedir(cliente_api, metodo, ruta, token=None):
    cabeceras = {"Authorization": f"Bearer {token}"} if token is not None else {}
    cuerpo = {"json": {"nombre": f"{PREFIJO_DATOS} notebook sin sesión"}} if metodo == "POST" else {}
    return cliente_api.request(metodo, ruta, headers=cabeceras, **cuerpo)


def _jwt_con_otra_clave(rol, minutos_de_vigencia=60):
    """Un JWT bien formado, vigente y con el rol que pide el endpoint, pero firmado con una clave que no es la del sistema."""
    ahora = datetime.now(timezone.utc)
    cuerpo = {"user_id": f"{PREFIJO_DATOS}000000", "role": rol, "username": PREFIJO_DATOS,
              "iat": ahora, "exp": ahora + timedelta(minutes=minutos_de_vigencia)}
    return jwt.encode(cuerpo, CLAVE_AJENA, algorithm="HS256")


def _jwt_del_sistema(rol, minutos_de_vigencia, usuario=f"{PREFIJO_DATOS}000000"):
    """Un JWT firmado por el propio código del sistema (`create_token`), con la vigencia pedida: así la prueba nunca lee
    el secreto. Una vigencia negativa da un token ya vencido."""
    from app.auth import jwt_auth

    anterior = jwt_auth.JWT_EXPIRE_MINUTES
    jwt_auth.JWT_EXPIRE_MINUTES = minutos_de_vigencia
    try:
        return jwt_auth.create_token(usuario, rol, PREFIJO_DATOS)
    finally:
        jwt_auth.JWT_EXPIRE_MINUTES = anterior


def _crear_tema_con_documento(tema_numero, nombre_archivo):
    """Crea un tema y un documento «Procesado» de prueba; devuelve sus identificadores. La limpieza por prueba los borra."""
    from app.db.database import SessionLocal
    from app.db.models import T_Documento, T_Estado_procesamiento, T_Expediente

    with SessionLocal() as db:
        procesado = db.query(T_Estado_procesamiento).filter(T_Estado_procesamiento.CT_Nombre_estado == "Procesado").one()
        tema = T_Expediente(CT_Num_expediente=tema_numero)
        documento = T_Documento(CT_Nombre_archivo=nombre_archivo, CT_Tipo_archivo="txt", CN_Id_estado=procesado.CN_Id_estado)
        tema.documentos.append(documento)
        db.add(tema)
        db.commit()
        return tema.CN_Id_expediente, documento.CN_Id_documento


def _guardar_fragmento(texto, tema_numero, nombre_archivo, id_tema, id_documento, registro_de_datos):
    """Guarda el fragmento con la función real del sistema y registra sus puntos para que se limpien."""
    from app.vectorstore.storage import store_in_vectorstore

    ids, cantidad = asyncio.run(store_in_vectorstore(
        texto=texto,
        metadatos={"nombre_archivo": nombre_archivo, "ruta_archivo": f"{PREFIJO_DATOS}/{nombre_archivo}", "tipo": "TXT"},
        CT_Num_expediente=tema_numero,
        id_expediente=id_tema,
        id_documento=id_documento,
    ))
    for identificador in ids:
        registro_de_datos.registrar_punto(identificador)
    return ids, cantidad


def _token(cliente_api, usuario):
    respuesta = cliente_api.post("/auth/login", json={"email": usuario.correo, "password": usuario.contrasena})
    assert respuesta.status_code == 200
    return respuesta.json()["access_token"]


def _contar(consulta, **parametros):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(text(consulta), parametros).scalar()


# --- RNF-07: sin token, 401 ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("metodo, ruta, rol", RUTAS_PROTEGIDAS)
def test_la_api_rechaza_con_401_una_peticion_sin_token(cliente_api, metodo, ruta, rol):
    """RNF-07: un endpoint protegido responde 401 «Token requerido» si la petición no trae token."""
    respuesta = _pedir(cliente_api, metodo, ruta)

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Token requerido"


@pytest.mark.parametrize("metodo, ruta, rol", RUTAS_PROTEGIDAS)
def test_la_api_rechaza_con_401_un_token_invalido(cliente_api, metodo, ruta, rol):
    """RNF-07: un token que no es un JWT firmado por el sistema también es 401, no un acceso ni un error del servidor."""
    respuesta = _pedir(cliente_api, metodo, ruta, token="no.es.un-token")

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Token inválido o expirado"


@pytest.mark.parametrize("metodo, ruta, rol", RUTAS_PROTEGIDAS)
def test_la_api_rechaza_con_401_un_jwt_firmado_con_otra_clave(cliente_api, metodo, ruta, rol):
    """RNF-07: un JWT bien formado, vigente y con el rol correcto, pero firmado con otra clave, es 401: la firma se
    verifica, no solo la forma del token."""
    respuesta = _pedir(cliente_api, metodo, ruta, token=_jwt_con_otra_clave(rol))

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Token inválido o expirado"


@pytest.mark.parametrize("metodo, ruta, rol", RUTAS_PROTEGIDAS)
def test_la_api_rechaza_con_401_un_jwt_vencido(cliente_api, metodo, ruta, rol):
    """RNF-07: un JWT firmado por el sistema pero ya vencido es 401, no un acceso."""
    respuesta = _pedir(cliente_api, metodo, ruta, token=_jwt_del_sistema(rol, minutos_de_vigencia=-60))

    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "Token inválido o expirado"


@pytest.mark.parametrize("ruta, fixture_de_usuario", [
    pytest.param("/usuarios/", "administrador", id="administrador"),
    pytest.param("/notebooks", "usuario_gubernamental", id="gubernamental"),
])
def test_control_un_jwt_vigente_firmado_por_el_sistema_si_pasa(cliente_api, request, ruta, fixture_de_usuario):
    """Control de las dos pruebas anteriores: el mismo JWT del sistema, pero vigente, SÍ es aceptado. Así el 401 del
    vencido se debe a su vencimiento y no a otra cosa (p. ej. la forma del cuerpo o el rol). Usa un usuario de prueba
    real para que la bitácora del sistema pueda registrar la consulta."""
    usuario = request.getfixturevalue(fixture_de_usuario)
    token = _jwt_del_sistema(usuario.rol, minutos_de_vigencia=60, usuario=usuario.cedula)
    respuesta = _pedir(cliente_api, "GET", ruta, token=token)

    assert respuesta.status_code == 200


# --- RA-02.6 (c): un fragmento inventado se guarda y se recupera con el modelo real ------------------------------------------

def test_un_fragmento_inventado_se_guarda_y_se_recupera_en_la_coleccion_de_pruebas(
    embeddings_reales, destino_de_pruebas, registro_de_datos
):
    """RA-02.6 (c): `store_in_vectorstore` guarda el fragmento con el modelo real; se recupera con el filtro
    `metadata.numero_expediente`, no con la clave sin el prefijo (la trampa de CLAUDE.md), y por búsqueda semántica."""
    from app.vectorstore import get_vectorstore_backend

    tema_numero = f"{PREFIJO_DATOS}-TEMA-HUMO"
    nombre_archivo = f"{PREFIJO_DATOS}_licencias.txt"
    id_tema, id_documento = _crear_tema_con_documento(tema_numero, nombre_archivo)

    ids, cantidad = _guardar_fragmento(TEXTO_INVENTADO, tema_numero, nombre_archivo, id_tema, id_documento, registro_de_datos)
    assert cantidad == 1 and len(ids) == 1

    cliente = destino_de_pruebas.qdrant
    puntos, _ = cliente.scroll(
        NOMBRE_PRUEBAS,
        scroll_filter=Filter(must=[FieldCondition(key="metadata.numero_expediente", match=MatchValue(value=tema_numero))]),
        with_payload=True,
        with_vectors=True,
    )
    # El almacén devuelve los identificadores sin guiones y Qdrant los entrega con guiones: se comparan como UUID.
    assert [uuid.UUID(str(p.id)) for p in puntos] == [uuid.UUID(str(i)) for i in ids]
    assert puntos[0].payload["page_content"] == TEXTO_INVENTADO
    assert puntos[0].payload["metadata"]["nombre_archivo"] == nombre_archivo
    assert puntos[0].payload["metadata"]["id_documento"] == id_documento
    assert len(puntos[0].vector) == DIMENSION

    sin_prefijo, _ = cliente.scroll(
        NOMBRE_PRUEBAS,
        scroll_filter=Filter(must=[FieldCondition(key="numero_expediente", match=MatchValue(value=tema_numero))]),
    )
    assert sin_prefijo == []  # la clave sin `metadata.` no encuentra nada: LangChain anida los metadatos

    resultados = asyncio.run(get_vectorstore_backend().search_by_text(
        "¿Cómo se renuevan las licencias de pesca?", top_k=3, expediente_filter=tema_numero
    ))
    assert [r["document_name"] for r in resultados] == [nombre_archivo]
    assert resultados[0]["expedient_id"] == tema_numero
    assert resultados[0]["documento_id"] == id_documento
    assert resultados[0]["content_preview"] == TEXTO_INVENTADO

    otro_tema = asyncio.run(get_vectorstore_backend().search_by_text(
        "¿Cómo se renuevan las licencias de pesca?", top_k=3, expediente_filter=f"{PREFIJO_DATOS}-OTRO-TEMA"
    ))
    assert otro_tema == []  # el filtro por tema acota de verdad


def test_la_busqueda_semantica_ordena_por_relevancia_con_fragmentos_de_asuntos_distintos(
    embeddings_reales, registro_de_datos
):
    """RA-02.6 (c): con dos fragmentos de temas y asuntos distintos, `search_by_text` (sin filtro de tema) pone primero el
    afín a la consulta, sea cual sea el orden en que se guardaron. Solo se compara el orden relativo y que el puntaje del
    afín sea mayor, nunca un puntaje exacto: así la prueba no depende de las cifras del modelo."""
    from app.vectorstore import get_vectorstore_backend

    pesca = (f"{PREFIJO_DATOS}-TEMA-HUMO-PESCA", f"{PREFIJO_DATOS}_licencias_de_pesca.txt", TEXTO_INVENTADO)
    eolica = (f"{PREFIJO_DATOS}-TEMA-HUMO-EOLICA", f"{PREFIJO_DATOS}_turbinas_eolicas.txt", TEXTO_OTRO_ASUNTO)
    # Se guarda primero el de las turbinas: el orden de inserción no debe decidir el resultado.
    for tema_numero, nombre_archivo, texto in (eolica, pesca):
        id_tema, id_documento = _crear_tema_con_documento(tema_numero, nombre_archivo)
        ids, cantidad = _guardar_fragmento(texto, tema_numero, nombre_archivo, id_tema, id_documento, registro_de_datos)
        assert cantidad == 1 and len(ids) == 1

    almacen = get_vectorstore_backend()
    consultas = [
        ("¿Cómo se renuevan las licencias de pesca?", pesca, eolica),
        ("¿Cada cuánto se lubrica el engranaje de las turbinas?", eolica, pesca),
    ]
    for consulta, afin, ajeno in consultas:
        resultados = asyncio.run(almacen.search_by_text(consulta, top_k=5))
        nombres = [r["document_name"] for r in resultados]
        assert afin[1] in nombres and ajeno[1] in nombres, nombres
        assert nombres.index(afin[1]) < nombres.index(ajeno[1]), f"«{consulta}» no puso primero {afin[1]}: {nombres}"
        puntaje = {r["document_name"]: r["similarity_score"] for r in resultados}
        assert puntaje[afin[1]] > puntaje[ajeno[1]]


# --- RA-02.7: el flujo completo con los dos roles y la rutina `limpiar` ----------------------------------------------------------

def test_el_flujo_completo_con_los_dos_roles_y_limpiar_deja_los_residuos_en_cero(
    cliente_api, administrador, usuario_gubernamental, destino_de_pruebas, registro_de_datos
):
    """RA-02.7, RNF-07: cada rol entra a lo suyo y no a lo del otro; el Usuario Gubernamental crea un notebook; lo que
    se creó (usuarios, notebook y registros de bitácora) queda en la base y la rutina `limpiar` lo deja en cero.

    Lo que demuestra es que `limpiar` funciona sobre un flujo completo: la prueba la llama ella misma para poder contar
    los residuos antes y después. Que la limpieza ocurra sola al terminar cada prueba NO se prueba aquí (la fixture
    automática correría después del final de la prueba): lo cubren `tests/infraestructura/test_residuos.py` y el conteo
    de residuos que falla el cierre de la sesión. Nombra RF-21 solo en lo del Administrador (ver el docstring del archivo)."""
    token_admin = _token(cliente_api, administrador)
    token_usuario = _token(cliente_api, usuario_gubernamental)

    usuarios = cliente_api.get("/usuarios/", headers={"Authorization": f"Bearer {token_admin}"})
    assert usuarios.status_code == 200
    cedulas = {u["CN_Id_usuario"] for u in usuarios.json()}
    assert {administrador.cedula, usuario_gubernamental.cedula} <= cedulas

    assert cliente_api.get("/usuarios/", headers={"Authorization": f"Bearer {token_usuario}"}).status_code == 403
    assert cliente_api.get("/notebooks", headers={"Authorization": f"Bearer {token_admin}"}).status_code == 403

    cabeceras = {"Authorization": f"Bearer {token_usuario}"}
    creado = cliente_api.post("/notebooks", headers=cabeceras, json={"nombre": f"{PREFIJO_DATOS} notebook del flujo"})
    assert creado.status_code == 200
    notebook = creado.json()
    assert notebook["clave_interna"] == f"NB-{notebook['id']}"
    listado = cliente_api.get("/notebooks", headers=cabeceras)
    assert listado.status_code == 200 and [n["id"] for n in listado.json()] == [notebook["id"]]

    assert _contar("SELECT COUNT(*) FROM T_Notebook WHERE CN_Id_usuario = :c", c=usuario_gubernamental.cedula) == 1
    assert _contar("SELECT COUNT(*) FROM T_Bitacora WHERE CN_Id_usuario = :c", c=administrador.cedula) >= 2  # inicio de sesión y consulta (RF-21)

    antes = datos.contar_residuos(destino_de_pruebas)
    assert antes.filas["T_Usuario"] == 2 and antes.filas["T_Notebook"] == 1 and antes.filas["T_Bitacora"] >= 2

    datos.limpiar(destino_de_pruebas, registro_de_datos)

    despues = datos.contar_residuos(destino_de_pruebas)
    assert despues.total == 0, despues.texto()
    assert _contar("SELECT COUNT(*) FROM T_Notebook WHERE CT_Nombre LIKE :p", p=f"{PREFIJO_DATOS}%") == 0
