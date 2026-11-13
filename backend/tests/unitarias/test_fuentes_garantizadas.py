"""La sección de fuentes de la respuesta del chat nunca falta (RF-12.1, RF-12.2).

Las instrucciones piden terminar toda respuesta con `**FUENTES:**`, pero el modelo local a veces la omite. Si termina una respuesta
sustancial sin ella, el servidor la agrega con los archivos y las rutas EXACTAS de los fragmentos que le dio al modelo. No la agrega
cuando el modelo ya la escribió, cuando dijo que no tiene información, cuando pide una aclaración o cuando la respuesta es corta
(un saludo). Los nombres son inventados.
"""
import pytest

from app.services.RAG.general_chains import MAXIMO_FUENTES_AGREGADAS, _fuentes_que_faltan

FUENTES = [
    ("PRUEBA informe.pdf", "uploads/PRUEBA-TEMA/PRUEBA informe.pdf"),
    ("PRUEBA anexo.docx", "uploads/PRUEBA-TEMA/PRUEBA anexo.docx"),
]
RESPUESTA = "Según los fragmentos recuperados, el documento inventado describe el plazo de diez días hábiles para presentar el recurso " \
            "ante la oficina y los requisitos que debe cumplir la solicitud, incluyendo los anexos."


@pytest.mark.requisito("RF-12.1")
def test_agrega_la_seccion_cuando_el_modelo_la_omitio():
    extra = _fuentes_que_faltan(RESPUESTA, FUENTES)
    assert extra == ("\n\n**FUENTES:**\n\n"
                     "- PRUEBA informe.pdf: (uploads/PRUEBA-TEMA/PRUEBA informe.pdf)\n"
                     "- PRUEBA anexo.docx: (uploads/PRUEBA-TEMA/PRUEBA anexo.docx)")


@pytest.mark.requisito("RF-12.1")
@pytest.mark.parametrize("respuesta", [
    RESPUESTA + "\n\n**FUENTES:**\n\n- PRUEBA informe.pdf: (uploads/PRUEBA-TEMA/PRUEBA informe.pdf)",
    RESPUESTA + "\n\nFuentes:\n- PRUEBA informe.pdf",
    RESPUESTA + "\n\n**fuentes**",
])
def test_no_agrega_nada_si_el_modelo_ya_escribio_las_fuentes(respuesta):
    assert _fuentes_que_faltan(respuesta, FUENTES) == ""


@pytest.mark.requisito("RF-12.1")
@pytest.mark.parametrize("respuesta", [
    "Los documentos recuperados no contienen información suficiente para responder esa pregunta. " + "Puedes reformularla. " * 6,
    "Los documentos recuperados no contiene información suficiente para responder. " + "Intenta con otros términos. " * 6,
    RESPUESTA + " ¿Te refieres al documento de 2023 o al de 2024?",
    "¡Hola! Soy el asistente de ServIA.",
    "",
])
def test_no_agrega_fuentes_a_un_rechazo_una_aclaracion_ni_una_respuesta_corta(respuesta):
    assert _fuentes_que_faltan(respuesta, FUENTES) == ""


@pytest.mark.requisito("RF-12.1")
def test_sin_fragmentos_enviados_no_hay_fuentes_que_agregar():
    assert _fuentes_que_faltan(RESPUESTA, []) == ""
    assert _fuentes_que_faltan(RESPUESTA, None) == ""


@pytest.mark.requisito("RF-12.1")
def test_agrega_como_mucho_las_primeras_fuentes():
    muchas = [(f"PRUEBA doc {i}.pdf", f"uploads/PRUEBA-TEMA/PRUEBA doc {i}.pdf") for i in range(MAXIMO_FUENTES_AGREGADAS + 4)]
    extra = _fuentes_que_faltan(RESPUESTA, muchas)
    assert extra.count("\n- ") == MAXIMO_FUENTES_AGREGADAS
    assert "PRUEBA doc 0.pdf" in extra and f"PRUEBA doc {MAXIMO_FUENTES_AGREGADAS}.pdf" not in extra
