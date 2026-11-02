"""Pruebas de T4 (spec 007: RF-12.61 y RF-11.66 en lo que toca al texto).

Se prueba la estructura de los cuatro textos de instrucciones (general, tema, notebook y reformulación), no
el texto exacto: tamaño máximo (≤ 20 % del presupuesto), presencia de cada regla de RF-12, ausencia de
voseo y de rastros del texto viejo, y que la reformulación no sea más larga que ninguna respuesta.
El conteo de tokens es el mismo estimador que usa el código (`presupuesto_contexto.tokens`).
"""
import re

import pytest

from app.config.contexto_config import CONFIGURACION as CFG
from app.services.RAG import presupuesto_contexto as pc
from app.services.RAG.prompts.answer_prompt import INSTRUCCIONES_GENERAL
from app.services.RAG.prompts.contextualize_prompt import INSTRUCCION_REFORMULACION
from app.services.RAG.prompts.expediente_prompt import instrucciones_tema
from app.services.RAG.prompts.notebook_prompt import instrucciones_notebook

MAX_TOKENS = int(CFG.presupuesto * 0.2)  # RF-12.61: ≤ 20 % del presupuesto (~1.430 tokens)
TEMA_60 = "T" * 60
NOTEBOOK_255 = "N" * 255

# Reglas de RF-12.61 que debe tener cada texto de respuesta (fragmentos de frase, sin texto exacto completo).
REGLAS_COMUNES = [
    "solo la información de los FRAGMENTOS RECUPERADOS",
    "No uses conocimiento general",
    "no contienen información suficiente",
    "Cita el archivo de origen",
    "forma ambigua",
    "aclaración",
    "en español",
    "FUENTES",
]

TEXTOS = {
    "general": lambda: INSTRUCCIONES_GENERAL,
    "tema": lambda: instrucciones_tema(TEMA_60),
    "notebook": lambda: instrucciones_notebook(NOTEBOOK_255),
    "reformulación": lambda: INSTRUCCION_REFORMULACION,
}

# Formas de voseo y rastros del texto viejo (plan §13).
VOSEO_SEGURO = re.compile(r"\b(vos|intentá|decí|usá|buscá|leé|respondé|tenés|podés|sabés|querés)\b", re.IGNORECASE)


@pytest.mark.parametrize("nombre", list(TEXTOS))
def test_instrucciones_estructura(nombre):
    """RF-12.61 / RF-11.66: tamaño, sin voseo ni rastros del texto viejo, y es un texto no vacío."""
    texto = TEXTOS[nombre]()
    assert texto.strip()
    assert pc.tokens(texto) <= MAX_TOKENS, f"{nombre}: {pc.tokens(texto)} tokens > {MAX_TOKENS}"
    assert len(texto) <= 5000
    assert not VOSEO_SEGURO.search(texto), VOSEO_SEGURO.search(texto)
    for rastro in ("JusticBot", "Intentá", "expediente judicial", "{{", "{context}", "{input}"):
        assert rastro not in texto, rastro


@pytest.mark.parametrize("nombre", ["general", "tema", "notebook"])
def test_instrucciones_reglas_de_rf12(nombre):
    """RF-12.61: cada texto de respuesta trae todas las reglas de RF-12."""
    texto = TEXTOS[nombre]()
    faltan = [r for r in REGLAS_COMUNES if r not in texto]
    assert not faltan, f"{nombre}: faltan {faltan}"
    assert "asistente de ServIA" in texto


def test_lo_propio_del_tema():
    """RF-12.61: el tema conserva la redacción de documentos."""
    texto = instrucciones_tema("PRUEBA tema")
    assert "REDACCIÓN DE DOCUMENTOS" in texto
    assert "[PENDIENTE: especificar]" in texto
    assert "«PRUEBA tema»" in texto and "{tema}" not in texto


def test_lo_propio_del_notebook_y_titulos_coinciden_con_el_armado():
    """RF-12.61 / RF-12.62: el notebook usa su lista y el tratamiento de imágenes; los títulos son los del armado."""
    texto = instrucciones_notebook("PRUEBA notebook")
    assert pc.TITULO_LISTA.strip(":\n") in texto
    assert pc.TITULO_FRAGMENTOS.strip(":\n") in texto
    assert "IMÁGENES" in texto and "Origen: documento escaneado" in texto
    assert 'Notebook "PRUEBA notebook": (<nombre del archivo>)' in texto
    assert "{notebook}" not in texto
    assert "{recordatorio_imagen}" not in texto
    for texto_chat in (INSTRUCCIONES_GENERAL, instrucciones_tema("PRUEBA tema")):
        assert pc.TITULO_FRAGMENTOS.strip(":\n") in texto_chat


@pytest.mark.parametrize("nombre", ["tema", "notebook"])
def test_nombre_con_llaves_no_rompe_el_armado(nombre):
    """El reemplazo es de texto: un nombre con llaves queda tal cual, sin error."""
    funcion = instrucciones_tema if nombre == "tema" else instrucciones_notebook
    texto = funcion("PRUEBA {context} {input} {x}")
    assert "PRUEBA {context} {input} {x}" in texto


def test_reformulacion_no_mas_larga_que_ninguna_respuesta():
    """RF-11.66: la reformulación es común a los tres chats y menor que cualquiera de sus instrucciones."""
    r = len(INSTRUCCION_REFORMULACION)
    for nombre in ("general", "tema", "notebook"):
        assert r <= len(TEXTOS[nombre]()), nombre
    assert "una línea" in INSTRUCCION_REFORMULACION
    assert "mensajes previos" in INSTRUCCION_REFORMULACION


def test_reformulacion_conserva_identificadores_y_solicitud():
    """RF-11.66: conserva identificadores exactos y reescribe solo la solicitud de un documento largo."""
    assert "Conserva exactos" in INSTRUCCION_REFORMULACION
    assert "reescribe solo la solicitud" in INSTRUCCION_REFORMULACION


def test_se_conserva_reformular_referencia_imagen():
    """Tarea T4: no se pierde la reformulación de referencias a imágenes del notebook."""
    from app.services.RAG.prompts.notebook_prompt import reformular_referencia_imagen
    assert callable(reformular_referencia_imagen)


def test_prompts_viejos_retirados():
    """T5 (decisión de Andrés, 29/10/2026): los textos y plantillas anteriores ya no existen; solo quedan los nuevos."""
    from app.services.RAG import prompts
    from app.services.RAG.prompts import answer_prompt, contextualize_prompt, expediente_prompt, notebook_prompt

    viejos = {
        answer_prompt: ["ANSWER_SYSTEM_PROMPT", "ANSWER_PROMPT"],
        expediente_prompt: ["get_expediente_system_prompt", "get_expediente_prompt"],
        notebook_prompt: ["get_notebook_system_prompt", "get_notebook_prompt"],
        contextualize_prompt: ["CONTEXTUALIZE_Q_SYSTEM_PROMPT", "CONTEXTUALIZE_Q_PROMPT"],
        prompts: ["ANSWER_PROMPT", "CONTEXTUALIZE_Q_PROMPT", "get_expediente_prompt", "get_notebook_prompt"],
    }
    for modulo, nombres in viejos.items():
        for nombre in nombres:
            assert not hasattr(modulo, nombre), f"{modulo.__name__}.{nombre} sigue existiendo"
