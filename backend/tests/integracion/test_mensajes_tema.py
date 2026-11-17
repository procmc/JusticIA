"""Mensajes en español del servidor con «tema» (spec 011, T3; RT-06.132). La API real, con un Usuario Gubernamental `PRUEBA`.

Los avisos y errores que el servidor devuelve y que el usuario puede ver decían «expediente»; ahora dicen «tema». Los nombres de
los parámetros y las rutas (`/archivos/expediente/…`, `expediente_number`) no cambian: son técnicos (RT-06).
"""
import uuid

import pytest
from pydantic import ValidationError

from app.schemas.ingesta_schemas import IngestaArchivosRequest
from tests.integracion.test_conversaciones_propias import conversaciones  # noqa: F401  (limpia las conversaciones que crea la prueba)
from tests.soporte.flujos import tema_heredado

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


@pytest.mark.requisito("RT-06.132")
@pytest.mark.parametrize("ruta", ["/archivos/expediente/{t}/archivos", "/archivos/expediente/{t}/archivo/PRUEBA_a.pdf"])
def test_un_formato_de_tema_invalido_en_archivos_dice_tema(cliente_api, sesion, ruta):
    respuesta = cliente_api.get(ruta.format(t="no-es-un-tema"), headers=sesion)
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Formato de tema inválido"


@pytest.mark.requisito("RT-06.132")
def test_el_esquema_de_ingesta_rechaza_un_formato_invalido_diciendo_tema():
    with pytest.raises(ValidationError) as error:
        IngestaArchivosRequest(CT_Num_expediente="no-es-un-tema")
    texto = str(error.value)
    assert "Formato de tema inválido" in texto
    assert "expediente inválido" not in texto


@pytest.mark.requisito("RT-06.132")
def test_asociar_el_tema_de_una_conversacion_responde_con_tema(
        cliente_api, sesion, usuario_gubernamental, registro_de_datos, conversaciones):
    tema = tema_heredado(registro_de_datos)
    sesion_chat = f"session_{usuario_gubernamental.correo}_{uuid.uuid4().hex[:8]}"
    conversaciones.append(sesion_chat)  # su usuario es un correo: la limpieza de la suite no la alcanza

    respuesta = cliente_api.post("/rag/update-expediente-context", headers=sesion,
                                 json={"session_id": sesion_chat, "expediente_number": tema, "action": "set"})

    assert respuesta.status_code == 200, respuesta.text
    mensaje = respuesta.json()["message"]
    assert mensaje == f"Contexto del tema {tema} actualizado correctamente"
    assert "expediente" not in mensaje.lower()
