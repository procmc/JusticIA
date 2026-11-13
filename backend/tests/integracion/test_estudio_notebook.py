"""Estudio del notebook, parte de integración (spec 010; RF-11.120 a RF-11.132, RF-12.120, RF-14.120 a RF-14.128, RNF-07.120,
RF-21.120 a RF-21.122, RN-01.120).

Usa la API real con un Usuario Gubernamental `PRUEBA`, SQL Server, Tika, Qdrant y los embeddings reales del entorno aislado, y el
Ollama simulado: lo que se comprueba es lo que RECIBE el modelo, lo que responde la API, lo que queda guardado y lo que queda en
la bitácora. Los datos son inventados (prefijo `PRUEBA`) y se limpian solos.
"""
import json
import time
import uuid
from dataclasses import dataclass

import pytest

from app.config import config
from app.services import estudio_service as modulo_estudio
from tests.integracion.conftest import RESPUESTA_SIMULADA, _consultar, _documento_procesado_en_el_notebook
from tests.integracion.test_aislamiento_notebooks import _documento_de_otro_asunto
from tests.soporte.flujos import DocumentoPrueba, crear_notebook
from tests.soporte.nombres import PREFIJO_DATOS

pytestmark = pytest.mark.filterwarnings("ignore:Results are not stored in backend:RuntimeWarning")

MENSAJE_SIN_FUENTES = "Marque al menos una fuente para generar un resultado."
MENSAJE_EN_CURSO = "Hay una generación en curso. Espere o cancélela."
MENSAJE_EXTENSAS = "Las fuentes marcadas son demasiado extensas. Desmarque algunas e intente de nuevo."
GENERAR, NOTA, QUITAR = 22, 23, 24
MAPA = '{"titulo": "Quebrada ficticia", "ramas": [{"titulo": "Laguna", "ramas": [{"titulo": "Patos azules", "ramas": []}]}, {"titulo": "Mapa", "ramas": []}]}'


def _eventos(respuesta) -> list:
    return [json.loads(linea[6:]) for linea in respuesta.text.splitlines() if linea.startswith("data: ")]


def _generar(cliente_api, cabeceras, notebook_id, tipo="resumen", **extra):
    return cliente_api.post(f"/estudio/{notebook_id}/generar", json={"tipo": tipo, **extra}, headers=cabeceras)


def _lista(cliente_api, cabeceras, notebook_id) -> list:
    r = cliente_api.get(f"/estudio/{notebook_id}/resultados", headers=cabeceras)
    assert r.status_code == 200
    return r.json()


def _marca_de_bitacora() -> int:
    return int(_consultar("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")[0][0])


def _filas(marca: int, tipo: int) -> list:
    return _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m AND CN_Id_tipo_accion = :t "
                      "ORDER BY CN_Id_bitacora", {"m": marca, "t": tipo})


def _documento_grande() -> DocumentoPrueba:
    """Un documento inventado de unos 45.000 caracteres (varias partes), con una marca al inicio y otra al final."""
    sufijo = uuid.uuid4().hex[:8]
    inicio, fin = f"INICIOGRANDE{sufijo}", f"FINGRANDE{sufijo}"
    parrafos = [f"Párrafo {i}: la quebrada ficticia {sufijo} desemboca en la laguna inventada número {i} y su caudal imaginario "
                f"cambia con las estaciones inventadas del año {2000 + i}. " * 3 for i in range(75)]
    texto = f"{PREFIJO_DATOS} {inicio}. " + "\n\n".join(parrafos) + f"\n\n{fin}."
    return DocumentoPrueba(nombre=f"{PREFIJO_DATOS}_{sufijo}.txt", contenido=texto.encode("utf-8"), frase=inicio + "|" + fin)


@dataclass
class Estudio:
    cabeceras: dict
    notebook: dict
    a: object
    id_a: int
    b: object
    id_b: int


@pytest.fixture
def estudio(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado):
    """Un notebook propio con dos fuentes Procesado de asuntos distintos."""
    ollama_simulado.responder(RESPUESTA_SIMULADA)
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook de estudio", registro_de_datos)
    a, id_a = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook)
    b, id_b = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, _documento_de_otro_asunto())
    return Estudio(sesion, notebook, a, id_a, b, id_b)


@pytest.mark.requisito("RF-11.120")
@pytest.mark.requisito("RF-12.120")
@pytest.mark.requisito("RF-14.120")
@pytest.mark.requisito("RF-14.121")
@pytest.mark.requisito("RF-21.120")
def test_genera_un_resumen_con_las_fuentes_marcadas_y_lo_guarda(cliente_api, estudio, ollama_simulado, usuario_gubernamental):
    nb = estudio.notebook["id"]
    ollama_simulado.responder(f"Resumen de PRUEBA: según [{estudio.a.nombre}] la quebrada desemboca en la laguna.")
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()

    r = _generar(cliente_api, estudio.cabeceras, nb, documentos=[estudio.id_a])
    assert r.status_code == 200, r.text
    eventos = _eventos(r)
    assert eventos[0]["type"] == "progreso" and eventos[-1]["type"] == "done"
    guardado = [e for e in eventos if e["type"] == "resultado"]
    assert len(guardado) == 1 and not [e for e in eventos if e["type"] == "error"]

    recibido = "\n".join(ollama_simulado.preguntas)
    assert estudio.a.frase in recibido and estudio.b.frase not in recibido, "solo la fuente marcada debe llegar al modelo"

    lista = _lista(cliente_api, estudio.cabeceras, nb)
    assert len(lista) == 1 and lista[0]["tipo"] == "resumen" and lista[0]["titulo"].startswith("Resumen · ")
    assert lista[0]["fuentes"] == [{"id": estudio.id_a, "nombre": estudio.a.nombre}] and lista[0]["fuentes_faltantes"] is False
    detalle = cliente_api.get(f"/estudio/{nb}/resultados/{lista[0]['id']}", headers=estudio.cabeceras).json()
    assert "Resumen de PRUEBA" in detalle["contenido"]

    filas = _filas(marca, GENERAR)
    assert len(filas) == 1
    assert "Resumen de PRUEBA" not in filas[0][0] + filas[0][1] and estudio.a.nombre not in filas[0][0] + filas[0][1], \
        "la bitácora no debe llevar el contenido ni el nombre de las fuentes (RF-21.122)"
    assert modulo_estudio.hay_generacion_en_curso(usuario_gubernamental.cedula) is False, "la marca de «generando» no se liberó"


@pytest.mark.requisito("RF-11.122")
@pytest.mark.requisito("RF-12.120")
def test_genera_un_informe(cliente_api, estudio, ollama_simulado):
    ollama_simulado.responder(f"# Informe de PRUEBA\n\n## Hallazgos\nSegún [{estudio.a.nombre}] hay una laguna.\n\n## Conclusiones\nNinguna.")
    r = _generar(cliente_api, estudio.cabeceras, estudio.notebook["id"], "informe")
    assert r.status_code == 200 and [e for e in _eventos(r) if e["type"] == "resultado"][0]["resultado"]["tipo"] == "informe"


@pytest.mark.requisito("RF-11.122")
@pytest.mark.requisito("RF-14.121")
def test_genera_un_mapa_mental_con_estructura_valida(cliente_api, estudio, ollama_simulado):
    nb = estudio.notebook["id"]
    ollama_simulado.responder(f"```json\n{MAPA}\n```")
    r = _generar(cliente_api, estudio.cabeceras, nb, "mapa_mental")
    resultado = [e for e in _eventos(r) if e["type"] == "resultado"][0]["resultado"]
    assert resultado["tipo"] == "mapa_mental" and resultado["contenido"]["titulo"] == "Quebrada ficticia"
    abierto = cliente_api.get(f"/estudio/{nb}/resultados/{resultado['id']}", headers=estudio.cabeceras).json()
    assert abierto["contenido"]["ramas"][0]["ramas"][0]["titulo"] == "Patos azules"


@pytest.mark.requisito("RF-11.125")
@pytest.mark.requisito("RF-21.120")
@pytest.mark.parametrize("tipo, salida", [("mapa_mental", "no es un mapa")])
def test_una_salida_invalida_se_reintenta_una_vez_y_no_se_guarda(cliente_api, estudio, ollama_simulado, tipo, salida):
    nb = estudio.notebook["id"]
    ollama_simulado.responder(salida)
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()

    r = _generar(cliente_api, estudio.cabeceras, nb, tipo, documentos=[estudio.id_a])
    errores = [e for e in _eventos(r) if e["type"] == "error"]
    assert errores and errores[0]["mensaje"] == "No se pudo generar el resultado. Intente de nuevo."
    assert len(ollama_simulado.preguntas) == 2, "debe llamar al modelo dos veces: el intento y un reintento"
    assert _lista(cliente_api, estudio.cabeceras, nb) == []
    filas = _filas(marca, GENERAR)
    assert len(filas) == 1 and "salida inválida" in filas[0][1]


@pytest.mark.requisito("RF-12.120")
@pytest.mark.parametrize("tipo", ["resumen", "informe"])
def test_un_resultado_sin_citas_se_guarda_con_las_fuentes_consultadas(cliente_api, estudio, ollama_simulado, tipo):
    # Con texto de imágenes mal reconocido el modelo a veces no nombra ninguna fuente: no se pierde el resultado, el sistema
    # agrega al final las fuentes de la selección (como el chat) y no se llama al modelo una segunda vez.
    nb = estudio.notebook["id"]
    ollama_simulado.responder("Un texto sin nombrar ninguna fuente.")
    ollama_simulado.preguntas.clear()
    r = _generar(cliente_api, estudio.cabeceras, nb, tipo, documentos=[estudio.id_a])
    eventos = _eventos(r)
    assert not [e for e in eventos if e["type"] == "error"]
    resultado = [e for e in eventos if e["type"] == "resultado"][0]["resultado"]
    assert resultado["contenido"].startswith("Un texto sin nombrar ninguna fuente.")
    assert "**Fuentes consultadas:**" in resultado["contenido"] and f"[{estudio.a.nombre}]" in resultado["contenido"]
    assert len(ollama_simulado.preguntas) == 1


@pytest.mark.requisito("RF-11.121")
def test_sin_fuentes_marcadas_responde_400_sin_llamar_al_modelo(cliente_api, estudio, ollama_simulado):
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()
    for ids in ([], [2 ** 62], [-1]):
        r = _generar(cliente_api, estudio.cabeceras, estudio.notebook["id"], documentos=ids)
        assert r.status_code == 400 and r.json()["detail"] == MENSAJE_SIN_FUENTES, ids
    assert not ollama_simulado.preguntas, "el modelo fue llamado"
    assert _filas(marca, GENERAR) == []
    assert _lista(cliente_api, estudio.cabeceras, estudio.notebook["id"]) == []


@pytest.mark.requisito("RF-11.126")
@pytest.mark.requisito("RF-11.127")
def test_un_contenido_largo_se_cubre_por_partes_con_avance(cliente_api, sesion, registro_de_datos, procesamiento_en_prueba,
                                                           ollama_simulado):
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook grande", registro_de_datos)
    grande = _documento_grande()
    _, id_grande = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, grande)
    ollama_simulado.responder(f"Notas de PRUEBA según [{grande.nombre}].")
    ollama_simulado.preguntas.clear()

    r = _generar(cliente_api, sesion, notebook["id"], documentos=[id_grande])
    eventos = _eventos(r)
    etapas = [e["etapa"] for e in eventos if e["type"] == "progreso"]
    assert any(e.startswith("Analizando parte 1 de ") for e in etapas) and etapas[-1] == "Redactando el resultado", etapas
    partes = [e for e in eventos if e["type"] == "progreso" and e["etapa"].startswith("Analizando")]
    assert len(partes) >= 2 and [e for e in eventos if e["type"] == "resultado"]
    # cada llamada recibe un tramo: todo el documento, de la marca inicial a la final, llegó al modelo (RF-11.126)
    inicio, fin = grande.frase.split("|")
    recibido = "\n".join(ollama_simulado.preguntas)
    assert inicio in recibido and fin in recibido
    assert len(ollama_simulado.preguntas) >= len(partes) + 1


@pytest.mark.requisito("RF-11.129")
@pytest.mark.requisito("RF-21.120")
def test_si_las_fuentes_superan_el_tamano_maximo_se_rechaza_antes_de_empezar(
        cliente_api, sesion, registro_de_datos, procesamiento_en_prueba, ollama_simulado, monkeypatch):
    notebook = crear_notebook(cliente_api, sesion, f"{PREFIJO_DATOS} notebook extenso", registro_de_datos)
    _, id_grande = _documento_procesado_en_el_notebook(cliente_api, sesion, procesamiento_en_prueba, notebook, _documento_grande())
    monkeypatch.setattr(config, "ESTUDIO_PARTES_MAXIMAS", 1)
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()

    r = _generar(cliente_api, sesion, notebook["id"], documentos=[id_grande])
    assert r.status_code == 400 and r.json()["detail"] == MENSAJE_EXTENSAS
    assert not ollama_simulado.preguntas
    filas = _filas(marca, GENERAR)
    assert len(filas) == 1 and "fuentes demasiado extensas" in filas[0][1]


@pytest.mark.requisito("RF-11.130")
@pytest.mark.requisito("RF-21.120")
def test_si_se_agota_el_tiempo_no_se_guarda_nada_y_se_libera_al_usuario(
        cliente_api, estudio, ollama_simulado, monkeypatch, usuario_gubernamental):
    nb = estudio.notebook["id"]
    monkeypatch.setattr(config, "ESTUDIO_TIEMPO_MAXIMO_SEGUNDOS", 0)
    marca = _marca_de_bitacora()

    errores = [e for e in _eventos(_generar(cliente_api, estudio.cabeceras, nb)) if e["type"] == "error"]
    assert errores and errores[0]["mensaje"].startswith("La generación tardó demasiado y se detuvo.")
    assert _lista(cliente_api, estudio.cabeceras, nb) == []
    assert "tiempo agotado" in _filas(marca, GENERAR)[0][1]
    assert modulo_estudio.hay_generacion_en_curso(usuario_gubernamental.cedula) is False


@pytest.mark.requisito("RF-11.132")
def test_si_el_motor_falla_se_avisa_sin_detalles_tecnicos_y_no_se_guarda(cliente_api, estudio, ollama_simulado):
    nb = estudio.notebook["id"]
    ollama_simulado.fallar(RuntimeError("detalle interno secreto del motor"))
    r = _generar(cliente_api, estudio.cabeceras, nb)
    errores = [e for e in _eventos(r) if e["type"] == "error"]
    assert errores and "secreto" not in r.text and _lista(cliente_api, estudio.cabeceras, nb) == []


@pytest.mark.requisito("RF-11.131")
def test_mientras_se_genera_no_se_puede_pedir_otra_generacion_ni_preguntar_en_el_chat(
        cliente_api, estudio, monkeypatch, usuario_gubernamental, ollama_simulado):
    nb = estudio.notebook["id"]
    monkeypatch.setitem(modulo_estudio._generando, usuario_gubernamental.cedula, time.monotonic() + 100)
    ollama_simulado.preguntas.clear()

    r = _generar(cliente_api, estudio.cabeceras, nb)
    assert r.status_code == 409 and r.json()["detail"] == MENSAJE_EN_CURSO
    chat = cliente_api.post("/rag/consulta-con-historial-stream", headers=estudio.cabeceras, json={
        "query": "¿Qué dicen las fuentes?", "session_id": f"session_{PREFIJO_DATOS}estudio_{uuid.uuid4().hex[:8]}",
        "notebook_id": str(nb)})
    assert chat.status_code == 409 and chat.json()["detail"] == MENSAJE_EN_CURSO
    assert not ollama_simulado.preguntas, "el modelo no debe llamarse mientras hay una generación en curso"

    modulo_estudio._generando.pop(usuario_gubernamental.cedula)
    assert _generar(cliente_api, estudio.cabeceras, nb).status_code == 200


@pytest.mark.requisito("RF-14.127")
@pytest.mark.requisito("RF-14.124")
@pytest.mark.requisito("RN-01.120")
@pytest.mark.requisito("RF-21.121")
def test_guarda_una_nota_y_al_quitarla_solo_se_da_de_baja(cliente_api, estudio):
    nb = estudio.notebook["id"]
    marca = _marca_de_bitacora()
    cuerpo = {"pregunta": "PRUEBA ¿qué dice la fuente?", "respuesta": f"PRUEBA respuesta con cita [{estudio.a.nombre}]",
              "fuentes": [estudio.a.nombre, estudio.a.nombre]}
    r = cliente_api.post(f"/estudio/{nb}/notas", json=cuerpo, headers=estudio.cabeceras)
    assert r.status_code == 200
    nota = r.json()
    assert nota["tipo"] == "nota" and nota["titulo"].startswith("Nota · ")
    assert nota["contenido"] == {"pregunta": cuerpo["pregunta"], "respuesta": cuerpo["respuesta"]}
    assert nota["fuentes"] == [{"id": None, "nombre": estudio.a.nombre}], "las fuentes repetidas se guardan una vez"
    assert [x["id"] for x in _lista(cliente_api, estudio.cabeceras, nb)] == [nota["id"]]

    q = cliente_api.delete(f"/estudio/{nb}/resultados/{nota['id']}", headers=estudio.cabeceras)
    assert q.status_code == 200 and q.json()["id"] == nota["id"]
    assert _lista(cliente_api, estudio.cabeceras, nb) == []
    assert cliente_api.get(f"/estudio/{nb}/resultados/{nota['id']}", headers=estudio.cabeceras).status_code == 404
    assert cliente_api.delete(f"/estudio/{nb}/resultados/{nota['id']}", headers=estudio.cabeceras).status_code == 404

    fila = _consultar("SELECT CF_Fecha_eliminacion FROM T_Resultado_Estudio WHERE CN_Id_resultado = :i", {"i": nota["id"]})
    assert len(fila) == 1 and fila[0][0] is not None, "la baja es lógica: la fila se conserva con su fecha (RN-01.120)"
    filas_nota = _filas(marca, NOTA)
    assert len(filas_nota) == 1 and "exitoso" in filas_nota[0][1]
    # quitar: la baja que sí se hizo y, del segundo borrado de una nota ya quitada, solo un intento fallido con su motivo
    filas_quitar = _filas(marca, QUITAR)
    assert len(filas_quitar) == 2 and "exitoso" in filas_quitar[0][1] and "resultado no disponible" in filas_quitar[1][1]
    for texto, info in filas_nota + filas_quitar:
        assert "PRUEBA" not in texto + info, "la bitácora no debe llevar el contenido de la nota (RF-21.122)"


@pytest.mark.requisito("RF-14.127")
def test_una_nota_sin_respuesta_se_rechaza(cliente_api, estudio):
    r = cliente_api.post(f"/estudio/{estudio.notebook['id']}/notas", headers=estudio.cabeceras,
                         json={"pregunta": "PRUEBA ¿?", "respuesta": "   ", "fuentes": []})
    assert r.status_code == 400
    assert _lista(cliente_api, estudio.cabeceras, estudio.notebook["id"]) == []


@pytest.mark.requisito("RF-14.123")
def test_si_se_quita_una_fuente_el_resultado_se_conserva_y_se_avisa(cliente_api, estudio, ollama_simulado):
    nb = estudio.notebook["id"]
    ollama_simulado.responder(f"Resumen de PRUEBA según [{estudio.a.nombre}].")
    _generar(cliente_api, estudio.cabeceras, nb, documentos=[estudio.id_a])
    resultado = _lista(cliente_api, estudio.cabeceras, nb)[0]
    assert resultado["fuentes_faltantes"] is False

    assert cliente_api.delete(f"/notebooks/{nb}/documentos/{estudio.id_a}", headers=estudio.cabeceras).status_code == 200
    despues = _lista(cliente_api, estudio.cabeceras, nb)
    assert [x["id"] for x in despues] == [resultado["id"]] and despues[0]["fuentes_faltantes"] is True
    abierto = cliente_api.get(f"/estudio/{nb}/resultados/{resultado['id']}", headers=estudio.cabeceras).json()
    assert "Resumen de PRUEBA" in abierto["contenido"] and abierto["fuentes"][0]["nombre"] == estudio.a.nombre


@pytest.mark.requisito("RF-14.125")
def test_los_resultados_no_son_fuentes_ni_documentos_del_notebook(cliente_api, estudio, ollama_simulado):
    nb = estudio.notebook["id"]
    ollama_simulado.responder(f"Resumen de PRUEBA según [{estudio.a.nombre}].")
    _generar(cliente_api, estudio.cabeceras, nb, documentos=[estudio.id_a])
    documentos = cliente_api.get(f"/notebooks/{nb}/documentos", headers=estudio.cabeceras).json()
    assert sorted(d["id"] for d in documentos) == sorted([estudio.id_a, estudio.id_b])


@pytest.mark.requisito("RNF-07.120")
@pytest.mark.requisito("RF-21.122")
def test_un_notebook_o_resultado_ajeno_o_inexistente_da_el_mismo_404(cliente_api, ajeno_ligero, ollama_simulado):
    otro = ajeno_ligero.cabeceras_otro
    ajeno = ajeno_ligero.notebook["id"]
    ollama_simulado.preguntas.clear()
    marca = _marca_de_bitacora()
    for destino in (ajeno, ajeno_ligero.id_inexistente, "abc", "05"):
        resultados = [
            _generar(cliente_api, otro, destino),
            cliente_api.get(f"/estudio/{destino}/resultados", headers=otro),
            cliente_api.get(f"/estudio/{destino}/resultados/1", headers=otro),
            cliente_api.post(f"/estudio/{destino}/notas", headers=otro, json={"pregunta": "PRUEBA", "respuesta": "PRUEBA", "fuentes": []}),
            cliente_api.delete(f"/estudio/{destino}/resultados/1", headers=otro),
        ]
        assert [r.status_code for r in resultados] == [404] * 5, destino
        assert {r.json()["detail"] for r in resultados} == {"Notebook no encontrado"}, destino
    assert not ollama_simulado.preguntas
    filas = _consultar("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :m", {"m": marca})
    for texto, info in filas:
        assert ajeno_ligero.notebook["clave_interna"] not in (texto or "") + (info or ""), "la bitácora no debe llevar la clave pedida"


@pytest.mark.requisito("RNF-07.120")
def test_un_resultado_de_otro_notebook_propio_es_un_404(cliente_api, estudio, registro_de_datos):
    nota = cliente_api.post(f"/estudio/{estudio.notebook['id']}/notas", headers=estudio.cabeceras,
                            json={"pregunta": "PRUEBA", "respuesta": "PRUEBA", "fuentes": []}).json()
    otro_notebook = crear_notebook(cliente_api, estudio.cabeceras, f"{PREFIJO_DATOS} otro notebook", registro_de_datos)
    r = cliente_api.get(f"/estudio/{otro_notebook['id']}/resultados/{nota['id']}", headers=estudio.cabeceras)
    assert r.status_code == 404 and r.json()["detail"] == "Resultado no encontrado en este notebook"
