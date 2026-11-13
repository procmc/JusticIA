"""El RTF ya no es un formato permitido, parte de integración (spec 006, cambio FFF1, T12; RF-05.52).

Con la API real, SQL Server, Tika y Qdrant del entorno aislado. Un `.rtf` subido a un tema no debe terminar Procesado ni dejar
fragmentos, y los demás archivos de la misma carga se procesan con normalidad. Datos inventados (prefijo `PRUEBA`).
"""
import uuid

import pytest
from tests.integracion.conftest import _consultar
from tests.soporte.flujos import cargar, contar_puntos, documento_de_prueba, exigir_estado, id_del_documento, tema_heredado
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


def _rtf_inventado() -> tuple:
    sufijo = uuid.uuid4().hex[:8]
    cuerpo = "{\\rtf1\\ansi\\deff0 {\\fonttbl{\\f0 Arial;}}\\f0\\fs24 " + (f"PRUEBA texto inventado {sufijo}. " * 12) + "\\par }"
    return f"{PREFIJO_DATOS}_{sufijo}.rtf", cuerpo.encode("ascii")


def _estado(nombre: str):
    filas = _consultar(
        "SELECT e.CT_Nombre_estado FROM T_Documento d JOIN T_Estado_procesamiento e ON e.CN_Id_estado = d.CN_Id_estado "
        "WHERE d.CT_Nombre_archivo = :n", {"n": nombre})
    return filas[0][0] if filas else None


@pytest.mark.requisito("RF-05.52")
def test_un_rtf_no_termina_procesado_y_los_demas_archivos_si(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba):
    """RF-05.52: de una carga con un `.rtf` y un `.txt`, el `.txt` queda Procesado con sus fragmentos y el `.rtf` nunca llega a
    Procesado ni deja fragmentos en Qdrant."""
    tema = tema_heredado(registro_de_datos)
    nombre_rtf, contenido_rtf = _rtf_inventado()
    texto = documento_de_prueba()

    respuesta = cargar(cliente_api, sesion, tema, [(nombre_rtf, contenido_rtf), (texto.nombre, texto.contenido)])
    assert respuesta.status_code == 200, respuesta.text
    procesamiento_en_prueba.procesar()

    id_texto = id_del_documento(texto.nombre)
    assert id_texto is not None
    exigir_estado(id_texto, "Procesado")
    assert _estado(nombre_rtf) in (None, "Error"), f"el .rtf no debe quedar Procesado: {_estado(nombre_rtf)}"
    assert contar_puntos(tema) > 0, "el .txt debía dejar fragmentos"
    id_rtf = id_del_documento(nombre_rtf)
    if id_rtf is not None:  # si el rechazo dejó una fila en Error, no tiene fragmentos
        assert _consultar("SELECT COUNT(*) FROM T_Documento d JOIN T_Estado_procesamiento e ON e.CN_Id_estado = d.CN_Id_estado "
                          "WHERE d.CN_Id_documento = :d AND e.CT_Nombre_estado = 'Procesado'", {"d": id_rtf})[0][0] == 0
