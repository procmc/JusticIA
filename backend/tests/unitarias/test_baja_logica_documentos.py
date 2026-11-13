"""Quitar una fuente del notebook con baja lógica, parte unitaria (spec 009b, cambio GG1, T11; RF-19.111, RF-19.112, RF-19.113).

Servicio con el repositorio, Qdrant y el disco simulados: lo que se comprueba es el ORDEN (fragmentos → archivo → baja), que un fallo
en cualquier paso no marque la baja y que un nuevo intento la termine, y que una fuente ya quitada sea un 404 uniforme. Nombres inventados.
"""
import asyncio
from types import SimpleNamespace

import pytest

CLAVE = "NB-7"
USUARIO = "U1"


class _Entorno:
    """Un `NotebookService` con el notebook `NB-7` (id 7, de `U1`) y una fuente; anota en `eventos` cada paso que ocurre."""

    def __init__(self, monkeypatch, falla=None, quitada=False):
        from app.services import notebook_service as modulo
        from app.services.notebook_service import NotebookService

        self.eventos, self.falla = [], falla
        documento = SimpleNamespace(
            CN_Id_documento=11, CT_Nombre_archivo="PRUEBA_a.pdf", esta_quitado=quitada,
            expedientes=[SimpleNamespace(CT_Num_expediente=CLAVE)])
        self.documento = documento
        notebook = SimpleNamespace(clave_interna=CLAVE, CN_Id_usuario=USUARIO)
        self.servicio = NotebookService()
        self.servicio.notebook_repo = SimpleNamespace(obtener_por_id=lambda db, i: notebook if i == 7 else None)

        def baja(db, doc, usuario_id, auto_commit=True):
            self._paso("baja")
            self.eventos[-1] = ("baja", usuario_id)
            doc.esta_quitado = True
            return doc

        # Sin `eliminar`: si el servicio todavía borra la fila, la prueba falla con AttributeError.
        self.servicio.documento_repo = SimpleNamespace(
            obtener_por_id=lambda db, i: None if (i != 11 or documento.esta_quitado) else documento,
            dar_de_baja=baja)

        entorno = self

        class _Vectores:
            async def delete_document_chunks(self, id_documento):
                entorno._paso("fragmentos")

        class _Ruta:
            def unlink(self):
                entorno._paso("archivo")

        monkeypatch.setattr(modulo, "get_vectorstore_backend", lambda: _Vectores())
        monkeypatch.setattr(modulo.file_management_service, "obtener_ruta_archivo", lambda clave, nombre: _Ruta())

    def _paso(self, nombre):
        self.eventos.append((nombre,))
        if self.falla == nombre:
            raise RuntimeError(f"fallo simulado en {nombre}")

    def quitar(self, id_documento=11):
        return asyncio.run(self.servicio.quitar_documento(None, 7, id_documento, USUARIO))


@pytest.mark.requisito("RF-19.111")
def test_quitar_elimina_fragmentos_y_archivo_y_marca_la_baja_en_ese_orden(monkeypatch):
    entorno = _Entorno(monkeypatch)
    notebook = entorno.quitar()
    assert [e[0] for e in entorno.eventos] == ["fragmentos", "archivo", "baja"]
    assert entorno.eventos[-1] == ("baja", USUARIO)
    assert notebook.clave_interna == CLAVE


@pytest.mark.requisito("RF-19.112")
@pytest.mark.parametrize("paso, esperados", [
    ("fragmentos", ["fragmentos"]),
    ("archivo", ["fragmentos", "archivo"]),
    ("baja", ["fragmentos", "archivo", "baja"]),
])
def test_un_fallo_no_marca_la_baja_antes_de_tiempo_y_el_reintento_la_termina(monkeypatch, paso, esperados):
    from app.services.notebook_service import ErrorAlQuitar

    entorno = _Entorno(monkeypatch, falla=paso)
    with pytest.raises(ErrorAlQuitar) as error:
        entorno.quitar()
    assert error.value.clave == CLAVE and error.value.documento_id == 11
    assert [e[0] for e in entorno.eventos] == esperados
    if paso != "baja":
        assert "baja" not in [e[0] for e in entorno.eventos], "la baja se marcó con un paso anterior sin cumplir"

    # Nuevo intento sin el fallo: repite lo ya cumplido (idempotente) y termina marcando la baja.
    entorno.falla = None
    entorno.eventos.clear()
    entorno.documento.esta_quitado = False
    entorno.quitar()
    assert [e[0] for e in entorno.eventos] == ["fragmentos", "archivo", "baja"]


@pytest.mark.requisito("RF-19.113")
def test_una_fuente_ya_quitada_es_404_uniforme(monkeypatch):
    from app.services.notebook_service import RecursoNoDisponible

    entorno = _Entorno(monkeypatch, quitada=True)
    with pytest.raises(RecursoNoDisponible):
        entorno.quitar()
    assert entorno.eventos == [], "no debe tocar fragmentos, archivo ni baja de algo ya quitado"


@pytest.mark.requisito("RF-19.113")
def test_si_el_repositorio_devolviera_una_quitada_el_servicio_tambien_la_rechaza(monkeypatch):
    """Defensa: aunque una consulta futura se olvide del filtro, `_documento_del_notebook` no entrega una fuente quitada."""
    from app.services.notebook_service import RecursoNoDisponible

    entorno = _Entorno(monkeypatch, quitada=True)
    entorno.servicio.documento_repo.obtener_por_id = lambda db, i: entorno.documento
    with pytest.raises(RecursoNoDisponible):
        entorno.quitar()
    assert entorno.eventos == []
