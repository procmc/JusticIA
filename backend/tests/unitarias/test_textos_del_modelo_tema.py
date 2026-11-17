"""Textos que se le dan al modelo con «tema» (spec 011, T5; RT-06.133). Sin base de datos ni modelo real.

El encabezado de cada documento del contexto del chat y las instrucciones del resumen de Temas Similares decían «expediente», y el
modelo puede repetirlo al usuario. Se prueba la estructura (el contexto trae «Tema: …», el resumen conserva sus campos), no el texto
de las respuestas del modelo, que no es determinista (testing.md). Aprobado por Andrés el 12/11/2026.
"""
import pytest
from langchain_core.documents import Document

from app.services.RAG.chunk_context_builder import _extract_document_metadata, _format_document_header
from app.services.busqueda_similares.response_parser import ResponseParser
from app.services.busqueda_similares.similarity_prompt_builder import create_similarity_summary_prompt

METADATOS = {"tipo_doc_label": "DOCUMENTO", "nombre_archivo": "PRUEBA_a.pdf", "expediente": "PRUEBA tema 99-500001-0001-PE", "total_chunks": 3}


@pytest.mark.requisito("RT-06.133")
def test_el_encabezado_de_cada_documento_del_contexto_dice_tema():
    encabezado = _format_document_header(1, METADATOS, "1-3")
    assert "Tema: PRUEBA tema 99-500001-0001-PE" in encabezado
    assert "Expediente" not in encabezado and "expediente" not in encabezado
    # Lo demás del encabezado no cambia.
    assert "Archivo: PRUEBA_a.pdf" in encabezado and "Mostrando chunks: 1-3 de 3 totales" in encabezado


@pytest.mark.requisito("RT-06.133")
def test_un_documento_sin_tema_dice_sin_tema_y_conserva_la_clave_interna():
    metadatos = _extract_document_metadata(Document(page_content="texto", metadata={"nombre_archivo": "PRUEBA_a.pdf"}))
    assert metadatos["expediente"] == "Sin tema", "la clave interna sigue siendo «expediente»; lo que se le entrega al modelo dice «Sin tema»"


@pytest.mark.requisito("RT-06.133")
def test_el_prompt_del_resumen_de_temas_similares_habla_de_tema_y_conserva_su_formato():
    prompt = create_similarity_summary_prompt("TEXTO DEL CONTEXTO", "PRUEBA-001")
    assert "expediente" not in prompt.lower(), "ninguna instrucción al modelo debe decir «expediente»"
    assert "CONTEXTO DEL TEMA PRUEBA-001:" in prompt and "TEXTO DEL CONTEXTO" in prompt
    for campo in ('"resumen"', '"palabras_clave"', '"factores_similitud"', '"conclusion"'):
        assert campo in prompt, f"el formato de salida debe conservar el campo {campo}"


@pytest.mark.requisito("RT-06.133")
def test_el_resumen_de_respaldo_dice_tema():
    resumen = ResponseParser()._crear_resumen_fallback("")
    texto = " ".join([resumen.resumen, *resumen.palabras_clave, *resumen.factores_similitud, resumen.conclusion])
    assert "expediente" not in texto.lower()
    assert "tema" in resumen.resumen.lower()
    assert "Materia Jurídica del Tema" in resumen.factores_similitud
