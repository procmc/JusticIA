"""Contexto del chat por tema y del notebook contra Qdrant real (spec 007, T5b; RF-11.69).

Sube y procesa por la API un documento inventado LARGO (muchos más fragmentos que los 8 que se envían al motor, con la frase
que responde la pregunta en el último) y consulta `POST /rag/consulta-con-historial-stream`. El motor es el simulado de la suite:
lo que se comprueba es lo que RECIBE, no el texto de una respuesta.
- RF-11.69: el fragmento relevante llega aunque esté al final del tema o del notebook (antes llegaban los primeros por número);
  el chat no trae fragmentos de otro tema; una pregunta sin relación igual trae los 8 fragmentos (sin umbral de similitud).
Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import uuid

import pytest

from tests.integracion.conftest import (
    _consultar_chat, _documento_procesado_en_el_notebook, _todo_lo_que_recibio_el_modelo,
)
from tests.soporte.flujos import (
    DocumentoPrueba, cargar, contar_puntos, crear_notebook, exigir_estado, id_del_documento, tema_heredado,
)
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

CHATS = ["tema", "notebook"]
FRAGMENTOS_ENVIADOS = 8  # fragmentos_por_consulta por omisión (RF-11.65)


def _documento_largo() -> DocumentoPrueba:
    """Un `PRUEBA_<uuid8>.txt` de 14 párrafos de relleno (cada uno forma su fragmento) y, al final, el que trae la frase única."""
    sufijo = uuid.uuid4().hex[:8]
    frase = f"la quebrada ficticia {sufijo} desemboca en la laguna inventada de los patos azules"
    relleno = [
        f"{PREFIJO_DATOS} párrafo {n} del inventario inventado: las sillas, los escritorios y las lámparas de la oficina ficticia "
        "se cuentan cada mes y se anotan en una planilla que nadie revisa. " * 8
        for n in range(14)
    ]
    texto = "\n\n".join(relleno + [f"{PREFIJO_DATOS} nota final del documento número {sufijo}: {frase}."])
    return DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=texto.encode("utf-8"), frase=frase)


def _pregunta_de(documento: DocumentoPrueba) -> str:
    """Pregunta por el contenido del último fragmento sin repetir la frase ni el nombre del archivo."""
    sufijo = documento.nombre[len(PREFIJO_DATOS) + 1:-len(".txt")]
    return f"¿Dónde desemboca la quebrada ficticia {sufijo}?"


def _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento, documento):
    """Crea el tema o el notebook, le sube y procesa el documento y devuelve `(clave, alcance_de_la_consulta)`."""
    if chat == "tema":
        tema = tema_heredado(registro_de_datos)
        respuesta = cargar(cliente_api, sesion, tema, [(documento.nombre, documento.contenido)])
        assert respuesta.status_code == 200, f"la carga respondió {respuesta.status_code}"
        [id_tarea] = respuesta.json()["task_ids"]
        assert procesamiento.procesar()[id_tarea].state == "SUCCESS"
        exigir_estado(id_del_documento(documento.nombre), "Procesado")
        clave, alcance = tema, {"expediente_number": tema}
    else:
        notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook {uuid.uuid4().hex[:6]}", registro_de_datos)
        _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento, notebook, documento)
        clave, alcance = notebook["clave_interna"], {"notebook_id": str(notebook["id"])}
    assert contar_puntos(clave) > FRAGMENTOS_ENVIADOS, "el documento de prueba debe tener más fragmentos que los enviados"
    return clave, alcance


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_recupera_por_relevancia(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 (regresión) · el fragmento con la frase, que es el último del documento, llega al motor aunque haya más de 8
    fragmentos: se recupera por relevancia y no los primeros por número."""
    documento = _documento_largo()
    _, alcance = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, documento)
    ollama_simulado.responder("Respuesta de PRUEBA.")
    pregunta = _pregunta_de(documento)
    assert documento.frase not in pregunta

    assert _consultar_chat(cliente_api, sesion, pregunta, **alcance).status_code == 200

    assert documento.frase in _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta), \
        "el fragmento relevante no llegó al motor"


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_no_mezcla_otro_tema(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 · la búsqueda por relevancia está filtrada: acotado a A, aunque la pregunta sea sobre el contenido de B, el
    motor recibe fragmentos de A y ni la frase ni el nombre del archivo de B."""
    doc_a, doc_b = _documento_largo(), _documento_largo()
    _, alcance_a = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, doc_a)
    _, alcance_b = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, doc_b)
    ollama_simulado.responder("Respuesta de PRUEBA.")
    pregunta_b = _pregunta_de(doc_b)

    # Control: acotado a B, la frase de B llega (la prueba distingue un chat filtrado de uno que no encuentra nada).
    assert _consultar_chat(cliente_api, sesion, pregunta_b, **alcance_b).status_code == 200
    assert doc_b.frase in _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta_b)

    ollama_simulado.preguntas.clear()
    assert _consultar_chat(cliente_api, sesion, pregunta_b, **alcance_a).status_code == 200
    recibido = _todo_lo_que_recibio_el_modelo(ollama_simulado, pregunta_b)
    assert doc_a.nombre in recibido, "el chat acotado no trajo fragmentos de su propio tema"
    assert doc_b.frase not in recibido and doc_b.nombre not in recibido


@pytest.mark.requisito("RF-11.69")
@pytest.mark.parametrize("chat", CHATS)
def test_pregunta_sin_relacion_trae_8(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """RF-11.69 · sin umbral de similitud: una pregunta sin relación con el contenido igual recibe los 8 fragmentos del tema o
    del notebook, en lugar de ninguno."""
    documento = _documento_largo()
    _, alcance = _alcance_con_documento(chat, cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, documento)
    ollama_simulado.responder("Respuesta de PRUEBA.")

    assert _consultar_chat(cliente_api, sesion, "¿Cuál es la capital de un país imaginario muy lejano?", **alcance).status_code == 200

    enviada = ollama_simulado.preguntas[-1]
    assert enviada.count("[Fragmento ") == FRAGMENTOS_ENVIADOS, f"llegaron {enviada.count('[Fragmento ')} fragmentos"
