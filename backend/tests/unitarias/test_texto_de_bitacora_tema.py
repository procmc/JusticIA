"""Descripción de los registros nuevos de la bitácora con «tema» (spec 011, T3; RF-21.130, RT-06.130). Sin base de datos.

El ERS y la interfaz hablan de «tema»; los servicios de auditoría todavía escribían «expediente» en el texto de cada registro nuevo.
Los datos que se guardan (claves, el tema y sus valores) no cambian, y los registros ya guardados tampoco (RN-01): solo la palabra
de la descripción. Se prueba con el servicio base simulado, que captura lo que se le pide registrar.
"""
import asyncio
from types import SimpleNamespace

import pytest

from app.repositories.expediente_repository import ExpedienteRepository
from app.services.bitacora.archivos_audit_service import archivos_audit_service
from app.services.bitacora.rag_audit_service import rag_audit_service
from app.services.bitacora.similarity_audit_service import similarity_audit_service

TEMA = "PRUEBA tema 99-500001-0001-PE"


class _Captura:
    """Un servicio base que anota el texto y la información adicional de cada registro que se le pide."""

    def __init__(self):
        self.llamadas = []

    async def registrar(self, **datos):
        self.llamadas.append(datos)
        return SimpleNamespace(**datos)


@pytest.fixture
def captura(monkeypatch):
    c = _Captura()
    for servicio in (archivos_audit_service, rag_audit_service, similarity_audit_service):
        monkeypatch.setattr(servicio, "bitacora_service", c)
    # Ningún tema existe en la base: el texto no depende de ello.
    monkeypatch.setattr(ExpedienteRepository, "obtener_por_numero", lambda self, db, numero: None)
    monkeypatch.setattr(rag_audit_service, "expediente_repo", SimpleNamespace(obtener_por_numero=lambda db, numero: None))
    return c


def _texto(captura):
    assert len(captura.llamadas) == 1, "debía registrar exactamente una acción"
    return captura.llamadas[0]["texto"]


@pytest.mark.requisito("RF-21.130")
def test_la_descarga_de_un_archivo_dice_tema(captura):
    asyncio.run(archivos_audit_service.registrar_descarga_archivo(
        None, "U1", "PRUEBA_a.pdf", expediente_numero=TEMA, exito=True))
    texto = _texto(captura)
    assert texto == f"Descarga de archivo: PRUEBA_a.pdf (tema: {TEMA})"
    assert captura.llamadas[0]["info_adicional"]["expediente_numero"] == TEMA, "la clave guardada no cambia"


@pytest.mark.requisito("RF-21.130")
def test_el_listado_de_archivos_dice_tema(captura):
    asyncio.run(archivos_audit_service.registrar_listado_archivos(None, "U1", TEMA, 3, exito=True))
    assert _texto(captura) == f"Listado de archivos del tema: {TEMA} (3 archivos)"


@pytest.mark.requisito("RF-21.130")
def test_el_error_al_listar_archivos_dice_tema(captura):
    asyncio.run(archivos_audit_service.registrar_listado_archivos(None, "U1", TEMA, 0, exito=False, error="fallo inventado"))
    assert _texto(captura).startswith(f"Error listando archivos del tema: {TEMA}")


@pytest.mark.requisito("RF-21.130")
def test_una_consulta_a_un_tema_dice_tema_y_conserva_su_clase_guardada(captura):
    asyncio.run(rag_audit_service.registrar_consulta_rag(
        None, "U1", "¿Qué dice el documento?", "sesion", tipo_consulta="expediente", expediente_numero=TEMA))
    llamada = captura.llamadas[0]
    assert llamada["texto"].startswith(f"Consulta RAG tema {TEMA}:")
    # Lo que se guarda para las estadísticas y los filtros no cambia: sigue siendo la clave técnica.
    assert llamada["info_adicional"]["tipo_consulta"] == "expediente"
    assert llamada["info_adicional"]["expediente_numero"] == TEMA


@pytest.mark.requisito("RF-21.130")
def test_una_consulta_de_un_notebook_y_una_general_no_cambian(captura):
    asyncio.run(rag_audit_service.registrar_consulta_rag(
        None, "U1", "pregunta", "sesion", tipo_consulta="notebook", expediente_numero="NB-12"))
    asyncio.run(rag_audit_service.registrar_consulta_rag(None, "U1", "pregunta", "sesion", tipo_consulta="general"))
    assert captura.llamadas[0]["texto"].startswith("Consulta RAG notebook NB-12:")
    assert captura.llamadas[1]["texto"].startswith("Consulta RAG general:")


@pytest.mark.requisito("RF-21.130")
@pytest.mark.parametrize("exito, error, esperado", [
    (True, None, f"Resumen IA generado para tema: {TEMA}"),
    (False, "fallo inventado", f"Error al generar resumen IA: {TEMA}"),
])
def test_el_resumen_ia_dice_tema(captura, exito, error, esperado):
    asyncio.run(similarity_audit_service.registrar_resumen_ia(
        None, "U1", TEMA, exito=exito, error=error, resultado={"total_documentos_analizados": 1}))
    assert _texto(captura).startswith(esperado)


@pytest.mark.requisito("RF-21.130")
def test_ningun_texto_nuevo_contiene_la_palabra_expediente(captura):
    asyncio.run(archivos_audit_service.registrar_descarga_archivo(None, "U1", "PRUEBA_a.pdf", expediente_numero=TEMA))
    asyncio.run(archivos_audit_service.registrar_listado_archivos(None, "U1", TEMA, 1))
    asyncio.run(rag_audit_service.registrar_consulta_rag(None, "U1", "pregunta", "s", tipo_consulta="expediente", expediente_numero=TEMA))
    asyncio.run(similarity_audit_service.registrar_resumen_ia(None, "U1", TEMA, exito=True, resultado={"total_documentos_analizados": 1}))
    for llamada in captura.llamadas:
        assert "expediente" not in llamada["texto"].lower(), llamada["texto"]


@pytest.mark.requisito("RF-21.130")
def test_la_busqueda_de_casos_similares_por_tema_dice_tema_y_guarda_su_modo(captura):
    asyncio.run(similarity_audit_service.registrar_busqueda_similares(
        None, "U1", "expediente", numero_expediente=TEMA, limite=5, umbral_similitud=0.8, exito=True,
        resultado={"total_resultados": 2, "casos_similares": []}))
    llamada = captura.llamadas[0]
    assert llamada["texto"].startswith(f"Búsqueda de casos similares (tema): '{TEMA}")
    assert llamada["info_adicional"]["modo_busqueda"] == "expediente", "el modo guardado es la clave técnica y no cambia"


@pytest.mark.requisito("RF-21.130")
def test_la_busqueda_por_descripcion_no_cambia(captura):
    asyncio.run(similarity_audit_service.registrar_busqueda_similares(
        None, "U1", "descripcion", texto_consulta="PRUEBA descripcion", exito=True, resultado={"total_resultados": 0}))
    assert captura.llamadas[0]["texto"].startswith("Búsqueda de casos similares (descripcion):")
