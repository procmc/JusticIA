"""Las rutas de las fuentes en la respuesta del chat (RF-12.1, RF-17.3, RNF-07.20), parte de integración.

El modelo a veces cambia la ortografía al copiar la ruta de una fuente y el enlace de descarga deja de funcionar. Con la API real, SQL
Server, Tika y Qdrant del entorno aislado y el Ollama simulado (que responde con la ruta mal copiada), se comprueba que el usuario
recibe la ruta registrada, y que NUNCA se «arregla» hacia un documento que no puede ver. Datos inventados (prefijo `PRUEBA`).
"""
import json
import uuid

import pytest

from tests.integracion.test_red_ingesta import _subir_y_procesar, _tema_libre
from tests.soporte.flujos import documento_de_prueba
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")


def _texto_recibido(respuesta) -> str:
    """El texto de la respuesta del chat: lo que el usuario ve, sin la estructura de los eventos."""
    trozos = []
    for linea in respuesta.text.splitlines():
        if linea.startswith("data: "):
            evento = json.loads(linea[6:])
            if evento.get("type") == "chunk":
                trozos.append(evento["content"])
    return "".join(trozos)


def _preguntar(cliente_api, cabeceras, **alcance):
    cuerpo = {"query": "¿Qué dice el documento inventado?", "session_id": f"session_{PREFIJO_DATOS}ruta_{uuid.uuid4().hex[:8]}", **alcance}
    return cliente_api.post("/rag/consulta-con-historial-stream", json=cuerpo, headers=cabeceras)


def _mal_copiada(ruta: str) -> str:
    """La ruta como la «corregiría» el modelo: con una tilde de más y en mayúsculas el nombre del archivo."""
    carpeta, nombre = ruta.rsplit("/", 1)
    return f"{carpeta}/{nombre.replace('PRUEBA', 'PRUÉBA').upper()}"


@pytest.mark.requisito("RF-12.1")
def test_la_ruta_que_el_modelo_copia_mal_se_devuelve_a_la_registrada(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    tema = _tema_libre(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [documento])
    registrada = f"uploads/{tema}/{documento.nombre}"
    escrita = _mal_copiada(registrada)
    assert escrita != registrada
    ollama_simulado.responder(f"Según el documento.\n\n**FUENTES:**\n- {documento.nombre}: ({escrita})\n")

    respuesta = _preguntar(cliente_api, sesion, expediente_number=tema)
    texto = _texto_recibido(respuesta)

    assert respuesta.status_code == 200
    assert f"({registrada})" in texto, texto
    assert escrita not in texto, "la ruta mal copiada llegó al usuario"


@pytest.mark.requisito("RF-12.1")
def test_una_ruta_ya_correcta_pasa_sin_cambios(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    tema = _tema_libre(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [documento])
    registrada = f"uploads/{tema}/{documento.nombre}"
    ollama_simulado.responder(f"**FUENTES:**\n- {documento.nombre}: ({registrada})\n")

    assert f"({registrada})" in _texto_recibido(_preguntar(cliente_api, sesion, expediente_number=tema))


@pytest.mark.requisito("RF-17.3")
@pytest.mark.requisito("RNF-07.20")
def test_nunca_se_arregla_una_ruta_hacia_un_documento_que_el_usuario_no_puede_ver(ajeno, cliente_api, ollama_simulado):
    """El documento del notebook de OTRO usuario no es una candidata: la ruta mal copiada pasa tal cual (y la descarga la rechaza)."""
    registrada = f"uploads/{ajeno.notebook['clave_interna']}/{ajeno.documento.nombre}"
    escrita = _mal_copiada(registrada)
    ollama_simulado.responder(f"**FUENTES:**\n- documento: ({escrita})\n")

    texto = _texto_recibido(_preguntar(cliente_api, ajeno.cabeceras_otro))

    assert escrita in texto, "la ruta del documento ajeno se alteró"
    assert registrada not in texto, "se reveló la ruta registrada de un documento que el usuario no puede ver"


@pytest.mark.requisito("RF-12.1")
def test_si_el_modelo_omite_las_fuentes_el_servidor_las_agrega_con_la_ruta_exacta(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    tema = _tema_libre(registro_de_datos)
    documento = documento_de_prueba()
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [documento])
    registrada = f"uploads/{tema}/{documento.nombre}"
    ollama_simulado.responder(
        "Según los fragmentos recuperados, el documento inventado describe la quebrada ficticia y su desembocadura en la laguna "
        "de los patos azules, con detalles de fechas, nombres y lugares inventados para las pruebas.")

    texto = _texto_recibido(_preguntar(cliente_api, sesion, expediente_number=tema))

    assert "**FUENTES:**" in texto, texto
    assert f"- {documento.nombre}: ({registrada})" in texto, texto


@pytest.mark.requisito("RF-12.1")
def test_no_se_agregan_fuentes_a_un_rechazo_del_modelo(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    tema = _tema_libre(registro_de_datos)
    _subir_y_procesar(cliente_api, sesion, procesamiento_en_prueba, tema, [documento_de_prueba()])
    ollama_simulado.responder(
        "Los documentos recuperados no contienen información suficiente para responder esa pregunta. Puedes reformularla con otros "
        "términos o preguntar por un tema distinto.")

    assert "FUENTES" not in _texto_recibido(_preguntar(cliente_api, sesion, expediente_number=tema))
