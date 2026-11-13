"""Baja lógica de la fuente por la API, parte de integración (spec 009b, cambio GG1, T12; RF-19.111 a RF-19.115, RF-21.103, RF-21.105).

Con la API real, SQL Server, Qdrant y Tika del entorno aislado y el Ollama simulado. El notebook trae dos fuentes: `a` se quita y `b`
queda. Datos inventados (prefijo `PRUEBA`) que se limpian solos.
"""
import pytest
from fastapi.testclient import TestClient

from tests.integracion.conftest import (
    _consultar, _consultar_chat, _pregunta_sobre,
)
from tests.integracion.test_estudio_notebook import (  # noqa: F401  (`estudio` es una fixture que se reutiliza)
    MENSAJE_SIN_FUENTES, _eventos, _filas, _generar, _lista, _marca_de_bitacora, estudio,
)
from tests.soporte.flujos import DocumentoPrueba, cargar, contexto_enviado
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

MENSAJE_CHAT_SIN_FUENTES = "Marque al menos una fuente para consultar."
MENSAJE_NO_SE_PUDO_QUITAR = "No se pudo quitar el documento. Intente de nuevo."
QUITAR_DOCUMENTO_NOTEBOOK = 17


def _quitar_por_api(cliente_api, estudio, id_documento):
    return cliente_api.delete(f"/notebooks/{estudio.notebook['id']}/documentos/{id_documento}", headers=estudio.cabeceras)


@pytest.mark.requisito("RF-19.113")
def test_la_fuente_quitada_no_aparece_en_ninguna_via_de_la_api(cliente_api, estudio, ollama_simulado):
    """RF-19.113: tras quitarla, la fuente no sale en la lista, el chat (aunque se marque), la generación del Estudio, la vista previa
    ni el renombrado, y volver a quitarla responde el mismo 404 uniforme que un identificador inexistente; la otra fuente sigue igual."""
    nb = estudio.notebook["id"]
    cab = estudio.cabeceras
    assert _quitar_por_api(cliente_api, estudio, estudio.id_a).status_code == 200

    lista = cliente_api.get(f"/notebooks/{nb}/documentos", headers=cab).json()
    assert [d["id"] for d in lista] == [estudio.id_b]

    # Chat: marcada solo la quitada, 400 sin llamar al modelo; marcadas las dos, el modelo solo recibe la que queda.
    ollama_simulado.preguntas.clear()
    solo_quitada = _consultar_chat(cliente_api, cab, _pregunta_sobre(estudio.a), notebook_id=str(nb), documentos=[estudio.id_a])
    assert solo_quitada.status_code == 400 and solo_quitada.json()["detail"] == MENSAJE_CHAT_SIN_FUENTES
    assert not ollama_simulado.preguntas, "el modelo fue llamado con una fuente quitada"
    pregunta = _pregunta_sobre(estudio.b)
    ambas = _consultar_chat(cliente_api, cab, pregunta, notebook_id=str(nb), documentos=[estudio.id_a, estudio.id_b])
    assert ambas.status_code == 200
    contexto = contexto_enviado(ollama_simulado).replace(pregunta, "")
    assert estudio.a.frase not in contexto and estudio.a.nombre not in contexto, "el chat recibió la fuente quitada"
    assert estudio.b.frase in contexto, "control: el chat no recibió la fuente que queda"

    # Estudio: marcada solo la quitada, 400; sin selección usa solo la que queda.
    sola = _generar(cliente_api, cab, nb, documentos=[estudio.id_a])
    assert sola.status_code == 400 and sola.json()["detail"] == MENSAJE_SIN_FUENTES
    ollama_simulado.responder(f"Resumen de PRUEBA según [{estudio.b.nombre}].")
    todas = _generar(cliente_api, cab, nb)
    resultado = [e for e in _eventos(todas) if e["type"] == "resultado"][0]["resultado"]
    assert [f["id"] for f in resultado["fuentes"]] == [estudio.id_b]

    # Vista previa y renombrado: 404; quitar de nuevo: el mismo 404 que un identificador que no existe.
    assert cliente_api.get(f"/notebooks/{nb}/documentos/{estudio.id_a}/archivo", headers=cab).status_code == 404
    assert cliente_api.put(f"/notebooks/{nb}/documentos/{estudio.id_a}", json={"nombre": "otro"}, headers=cab).status_code == 404
    otra_vez = _quitar_por_api(cliente_api, estudio, estudio.id_a)
    inexistente = _quitar_por_api(cliente_api, estudio, estudio.id_b + 1_000_000)
    assert otra_vez.status_code == 404 and (otra_vez.status_code, otra_vez.json()) == (inexistente.status_code, inexistente.json())
    # La que queda sigue completa.
    assert cliente_api.get(f"/notebooks/{nb}/documentos/{estudio.id_b}/archivo", headers=cab).status_code == 200


@pytest.mark.requisito("RF-19.115")
def test_un_resultado_previo_del_estudio_conserva_el_nombre_de_la_fuente_quitada(cliente_api, estudio, ollama_simulado):
    """RF-19.115: el resultado generado con una fuente que luego se quita sigue abriéndose, con su nombre y la marca de fuente faltante."""
    nb = estudio.notebook["id"]
    ollama_simulado.responder(f"Resumen de PRUEBA según [{estudio.a.nombre}].")
    generado = _generar(cliente_api, estudio.cabeceras, nb, documentos=[estudio.id_a])
    assert [e for e in _eventos(generado) if e["type"] == "resultado"], generado.text
    assert _quitar_por_api(cliente_api, estudio, estudio.id_a).status_code == 200

    lista = _lista(cliente_api, estudio.cabeceras, nb)
    assert len(lista) == 1
    assert lista[0]["fuentes"] == [{"id": estudio.id_a, "nombre": estudio.a.nombre}] and lista[0]["fuentes_faltantes"] is True
    abierto = cliente_api.get(f"/estudio/{nb}/resultados/{lista[0]['id']}", headers=estudio.cabeceras)
    assert abierto.status_code == 200 and "Resumen de PRUEBA" in abierto.json()["contenido"]


@pytest.mark.requisito("RF-19.114")
def test_el_nombre_de_una_fuente_quitada_se_puede_reutilizar(cliente_api, sesion, estudio, procesamiento_en_prueba):
    """RF-19.114: renombrar otra fuente con el nombre de la quitada no choca, y un archivo nuevo con ese nombre se guarda sin sufijo."""
    nb = estudio.notebook["id"]
    assert _quitar_por_api(cliente_api, estudio, estudio.id_a).status_code == 200

    base_de_a = estudio.a.nombre[: -len(".txt")]
    renombrada = cliente_api.put(f"/notebooks/{nb}/documentos/{estudio.id_b}", json={"nombre": base_de_a}, headers=estudio.cabeceras)
    assert renombrada.status_code == 200, renombrada.text

    de_nuevo = DocumentoPrueba(nombre=estudio.a.nombre, contenido=estudio.a.contenido, frase=estudio.a.frase)
    # Se sube a mano: `id_del_documento` supone un solo documento por nombre y ahora hay dos (la quitada y la nueva).
    carga = cargar(cliente_api, sesion, estudio.notebook["clave_interna"], [(de_nuevo.nombre, de_nuevo.contenido)])
    assert carga.status_code == 200, carga.text
    assert procesamiento_en_prueba.procesar()[carga.json()["task_ids"][0]].state == "SUCCESS"
    nuevos = _consultar("SELECT CN_Id_documento FROM T_Documento WHERE CT_Nombre_archivo = :n AND CF_Fecha_baja IS NULL",
                        {"n": de_nuevo.nombre})
    assert len(nuevos) == 1
    id_nuevo = nuevos[0][0]
    assert id_nuevo != estudio.id_a
    guardado = _consultar("SELECT CT_Nombre_archivo FROM T_Documento WHERE CN_Id_documento = :d", {"d": id_nuevo})[0][0]
    assert guardado == estudio.a.nombre, "el archivo nuevo debía guardarse sin sufijo: la quitada ya no ocupa el nombre en disco"
    # La fila quitada sigue ahí, con su nombre.
    assert _consultar("SELECT CT_Nombre_archivo FROM T_Documento WHERE CN_Id_documento = :d", {"d": estudio.id_a})[0][0] == estudio.a.nombre


@pytest.mark.requisito("RF-21.105")
@pytest.mark.requisito("RF-21.103")
def test_la_bitacora_de_quitar_no_trae_nombres_y_su_numero_llega_a_la_fila(cliente_api, estudio):
    """RF-21.105, RF-21.103: una fila de «Quitar Documento de Notebook» con la clave y el número del documento, sin su nombre; y ese
    número ahora lleva a la fila quitada, con su nombre y quién la quitó."""
    marca = _marca_de_bitacora()
    assert _quitar_por_api(cliente_api, estudio, estudio.id_a).status_code == 200

    filas = _filas(marca, QUITAR_DOCUMENTO_NOTEBOOK)
    assert len(filas) == 1
    texto = f"{filas[0][0]} {filas[0][1]}"
    assert estudio.notebook["clave_interna"] in texto and str(estudio.id_a) in texto
    assert estudio.a.nombre not in texto and estudio.a.nombre[: -len(".txt")] not in texto, "la bitácora no debe llevar nombres (RNF-07.24)"
    fila = _consultar("SELECT CT_Nombre_archivo, CN_Id_usuario_baja FROM T_Documento WHERE CN_Id_documento = :d", {"d": estudio.id_a})
    assert fila[0][0] == estudio.a.nombre and fila[0][1] is not None


@pytest.mark.requisito("RF-19.112")
def test_un_fallo_al_marcar_la_baja_deja_el_documento_listado_y_el_reintento_la_termina(cliente_api, estudio, monkeypatch):
    """RF-19.112: si falla solo la marca de la baja, la respuesta es el 500 de siempre, la fila sigue activa y listada, y un nuevo
    intento termina la baja."""
    from app.repositories.documento_repository import DocumentoRepository

    nb = estudio.notebook["id"]
    original = DocumentoRepository.dar_de_baja
    interruptor = {"activa": True}

    def _falla(self, db, documento, usuario_id, auto_commit=True):
        if interruptor["activa"]:
            raise RuntimeError("PRUEBA fallo interno al marcar la baja en /srv/PRUEBA_interno/almacen.py")
        return original(self, db, documento, usuario_id, auto_commit)

    monkeypatch.setattr(DocumentoRepository, "dar_de_baja", _falla)
    sin_relanzar = TestClient(cliente_api.app, raise_server_exceptions=False)
    ruta = f"/notebooks/{nb}/documentos/{estudio.id_a}"

    primera = sin_relanzar.delete(ruta, headers=estudio.cabeceras)
    assert primera.status_code == 500 and primera.json()["detail"] == MENSAJE_NO_SE_PUDO_QUITAR
    assert "PRUEBA_interno" not in primera.text and "Traceback" not in primera.text
    assert tuple(_consultar("SELECT CF_Fecha_baja, CN_Id_usuario_baja FROM T_Documento WHERE CN_Id_documento = :d",
                            {"d": estudio.id_a})[0]) == (None, None)
    assert estudio.id_a in [d["id"] for d in cliente_api.get(f"/notebooks/{nb}/documentos", headers=estudio.cabeceras).json()]

    interruptor["activa"] = False
    segunda = sin_relanzar.delete(ruta, headers=estudio.cabeceras)
    assert segunda.status_code == 200
    assert _consultar("SELECT CF_Fecha_baja FROM T_Documento WHERE CN_Id_documento = :d", {"d": estudio.id_a})[0][0] is not None


@pytest.mark.requisito("RF-19.113")
@pytest.mark.requisito("RF-19.111")
def test_quitar_una_fuente_mientras_se_procesa_no_deja_fragmentos(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, monkeypatch):
    """RF-19.111, RF-19.113 (decisión D5 del plan): si el usuario quita una fuente Pendiente mientras el Worker la procesa, al terminar
    la tarea no queda ningún fragmento de ese documento, la fila sigue con su baja y la fuente no se lista."""
    import app.services.ingesta.file_management.document_processor as procesador
    from tests.integracion.test_red_notebooks import _puntos_del_tema
    from tests.soporte.flujos import crear_notebook, documento_de_prueba

    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook quitar al procesar", registro_de_datos)
    clave = notebook["clave_interna"]
    documento = documento_de_prueba()
    original = procesador.store_in_vectorstore
    quitado = {}

    async def _quitando_justo_antes_de_indexar(*args, **kwargs):
        """La fila ya existe (Pendiente) y aún no hay fragmentos: el usuario la quita en ese instante."""
        id_documento = kwargs["id_documento"]
        quitado["id"] = id_documento
        quitado["respuesta"] = cliente_api.delete(f"/notebooks/{notebook['id']}/documentos/{id_documento}", headers=sesion)
        return await original(*args, **kwargs)

    monkeypatch.setattr(procesador, "store_in_vectorstore", _quitando_justo_antes_de_indexar)
    carga = cargar(cliente_api, sesion, clave, [(documento.nombre, documento.contenido)])
    assert carga.status_code == 200, carga.text
    procesamiento_en_prueba.procesar()

    assert quitado.get("respuesta") is not None and quitado["respuesta"].status_code == 200, "la fuente no se pudo quitar en medio"
    id_documento = quitado["id"]
    huerfanos = [p for p in _puntos_del_tema(clave) if p.payload["metadata"]["id_documento"] == id_documento]
    assert huerfanos == [], "quedaron fragmentos de una fuente quitada"
    assert _consultar("SELECT CF_Fecha_baja FROM T_Documento WHERE CN_Id_documento = :d", {"d": id_documento})[0][0] is not None
    assert id_documento not in [d["id"] for d in cliente_api.get(f"/notebooks/{notebook['id']}/documentos", headers=sesion).json()]
