"""Red de seguridad de las cargas con archivos aceptados y rechazados (spec 004, tarea 9a, bloque F;
RF-05.22, RF-05.23 en lo que entrega el sistema, RF-21).

Sube por `POST /ingesta/archivos`, como lo haría la interfaz de Ingesta o de un notebook, con un Usuario Gubernamental
`PRUEBA`, el encolado interceptado (la tarea no se ejecuta) y la carpeta de documentos desviada a una temporal:
- RF-05.22: la respuesta añade los aceptados (cuántos y su tarea) y los rechazados (cuántos, su posición y su motivo en
  español) sin tocar la lista de identificadores; la confirmación (`message`) y el total cuentan solo los aceptados.
- RF-05.22 y RF-21: la carga iniciada se registra solo con al menos un aceptado y los cuenta; cada archivo rechazado
  (nombre no válido, vacío, guardado fallido, error interno) deja una fila con su motivo, sin su nombre ni el tema.
- RF-05.23 (contenido): lo que la pantalla presenta, sin el nombre rechazado y con la confirmación de solo los aceptados.

Son regresiones: se escribieron contra la spec y se vieron en rojo con el comportamiento anterior. Los datos son
inventados (prefijo `PRUEBA` o temas registrados) y se limpian solos.
"""
import json

import pytest
from sqlalchemy import text

from tests.soporte.flujos import (
    cargar, contar_puntos, documento_de_prueba, exigir_estado, exigir_progreso, id_del_documento, tema_heredado,
)

CARGA_DOCUMENTOS = 2  # TiposAccion.CARGA_DOCUMENTOS

NOMBRE_NO_VALIDO = "../PRUEBA_nombre_no_valido.txt"
NOMBRE_VACIO = "PRUEBA_vacio.txt"
MENSAJE_TODOS_RECHAZADOS = "No se aceptó ningún archivo. Revise el motivo de cada uno."
MOTIVOS = {"nombre de archivo no válido", "archivo vacío", "no se pudo guardar el archivo", "error interno"}


@pytest.fixture
def sesion(iniciar_sesion, usuario_gubernamental):
    return iniciar_sesion(usuario_gubernamental)


@pytest.fixture
def parchar_instancia():
    """Sustituye un método de una instancia y, al terminar, la deja exactamente como estaba (con o sin ese atributo
    propio). `monkeypatch.setattr` sobre una instancia deja al deshacer el método original en ella, y eso taparía los
    parches de clase de otras pruebas."""
    hechos = []

    def parchar(objeto, nombre, nuevo):
        hechos.append((objeto, nombre, nombre in vars(objeto), vars(objeto).get(nombre)))
        setattr(objeto, nombre, nuevo)

    yield parchar
    for objeto, nombre, estaba, previo in reversed(hechos):
        if estaba:
            setattr(objeto, nombre, previo)
        else:
            delattr(objeto, nombre)


# --- Lectura de la bitácora y de la carpeta temporal ---------------------------------------------------------------------

def _ultimo_id_de_bitacora() -> int:
    from app.db.database import engine

    with engine.connect() as conexion:
        return int(conexion.execute(text("SELECT COALESCE(MAX(CN_Id_bitacora), 0) FROM T_Bitacora")).scalar())


def _filas_desde(ultimo_id: int, cedula: str) -> list:
    """Las filas de carga de documentos de ese usuario creadas después de `ultimo_id`: [{texto, info}] en orden."""
    from app.db.database import engine

    with engine.connect() as conexion:
        filas = conexion.execute(
            text("SELECT CT_Texto, CT_Informacion_adicional FROM T_Bitacora WHERE CN_Id_bitacora > :d "
                 "AND CN_Id_tipo_accion = :t AND CN_Id_usuario = :u ORDER BY CN_Id_bitacora"),
            {"d": ultimo_id, "t": CARGA_DOCUMENTOS, "u": cedula}).fetchall()
    return [{"texto": f[0] or "", "info": json.loads(f[1]) if f[1] else {}} for f in filas]


def _iniciadas(filas: list) -> list:
    return [f for f in filas if f["info"].get("fase") == "iniciado"]


def _rechazos(filas: list) -> list:
    return [f for f in filas if f["texto"].startswith("Carga rechazada")]


def _archivos_del_tema(carpeta_archivos, tema: str) -> list:
    carpeta = carpeta_archivos / "uploads" / tema
    return sorted(p.name for p in carpeta.iterdir()) if carpeta.exists() else []


def _sin_rastros_del_nombre(textos, nombre: str) -> None:
    """Ni el nombre pedido ni su parte reconocible aparecen en lo que se entrega o se registra (RNF-07.24)."""
    pieza = nombre.split("/")[-1]
    for contenido in textos:
        assert nombre not in contenido and pieza not in contenido, contenido


# --- RF-05.22: carga mixta, a un tema y al notebook propio ----------------------------------------------------------------

def _comprobar_carga_mixta(cliente_api, sesion, usuario, carpeta_archivos, tema: str) -> None:
    """Un válido, uno vacío y uno de nombre no válido al `tema`: la respuesta, el disco y la bitácora."""
    valido = documento_de_prueba()
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, tema,
                       [(valido.nombre, valido.contenido), (NOMBRE_VACIO, b""), (NOMBRE_NO_VALIDO, b"PRUEBA contenido")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["aceptados"] == {"cantidad": 1, "tareas": [{"posicion": 1, "id_tarea": "PRUEBA-tarea-1"}]}
    assert cuerpo["rechazados"] == {"cantidad": 2, "archivos": [
        {"posicion": 2, "motivo": "archivo vacío"}, {"posicion": 3, "motivo": "nombre de archivo no válido"}]}
    assert cuerpo["total_files"] == 1
    assert cuerpo["message"] == "1 archivo enviado a procesamiento"
    assert cuerpo["expediente"] == tema
    # Solo el válido quedó guardado y encolado.
    assert _archivos_del_tema(carpeta_archivos, tema) == [valido.nombre]
    # Filas nuevas exactamente: una de carga iniciada (1 aceptado, 2 rechazados) y una de rechazo por cada rechazado.
    filas = _filas_desde(ultimo_id, usuario.cedula)
    assert sorted(f["texto"] for f in filas) == sorted([
        "Iniciado: 1 archivo(s)", "Carga rechazada: archivo vacío", "Carga rechazada: nombre de archivo no válido"])
    iniciada = _iniciadas(filas)[0]["info"]
    assert (iniciada["archivos_aceptados"], iniciada["archivos_rechazados"]) == (1, 2)
    assert iniciada["expediente"] == tema and iniciada["task_id"] == "PRUEBA-tarea-1"
    # Los rechazos solo llevan su motivo: ni el nombre ni el tema.
    for fila in _rechazos(filas):
        assert set(fila["info"]) >= {"motivo", "error", "tipo_error"} and "expediente" not in fila["info"]
        assert tema not in json.dumps(fila["info"]) + fila["texto"]
    _sin_rastros_del_nombre([respuesta.text] + [f["texto"] + json.dumps(f["info"]) for f in filas], NOMBRE_NO_VALIDO)
    _sin_rastros_del_nombre([f["texto"] + json.dumps(f["info"]) for f in _rechazos(filas)], NOMBRE_VACIO)


@pytest.mark.requisito("RF-05.22")
@pytest.mark.requisito("RF-21.7")
def test_carga_mixta_a_un_tema(cliente_api, sesion, usuario_gubernamental, registro_de_datos, carpeta_archivos,
                               encolado_interceptado):
    """RF-05.22: a un tema, un válido, uno vacío y uno de nombre no válido dan éxito con 1 aceptado (con su tarea), 2
    rechazados (con posición y motivo), total 1 y confirmación con 1; la bitácora tiene exactamente la carga iniciada
    (1 aceptado, 2 rechazados) y un rechazo por motivo; ningún cuerpo ni fila contiene el nombre no válido."""
    tema = tema_heredado(registro_de_datos)

    _comprobar_carga_mixta(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, tema)

    assert [p.id for p in encolado_interceptado.pendientes] == ["PRUEBA-tarea-1"]


@pytest.mark.requisito("RF-05.22")
def test_carga_mixta_al_notebook_propio(cliente_api, sesion, usuario_gubernamental, notebook_de_prueba, carpeta_archivos,
                                        encolado_interceptado):
    """RF-05.22: lo mismo cargando al notebook propio (su tema es la clave interna `NB-<id>`)."""
    _comprobar_carga_mixta(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, notebook_de_prueba.clave_interna)

    assert [p.tema for p in encolado_interceptado.pendientes] == [notebook_de_prueba.clave_interna]


@pytest.mark.requisito("RF-05.22")
def test_lista_de_identificadores_sin_cambios(cliente_api, sesion, registro_de_datos, carpeta_archivos,
                                              encolado_interceptado):
    """RF-05.22 (contrato aditivo): `task_ids` conserva su largo, su orden y su forma (texto para el aceptado, objeto
    con `error` y `message` para cada rechazado en su posición) y siguen todos los campos que ya se entregaban. Es una
    caracterización: pasa antes y después del cambio."""
    tema = tema_heredado(registro_de_datos)
    valido = documento_de_prueba()

    respuesta = cargar(cliente_api, sesion, tema,
                       [(NOMBRE_VACIO, b""), (valido.nombre, valido.contenido), (NOMBRE_NO_VALIDO, b"PRUEBA contenido")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["task_ids"] == [
        {"error": True, "message": "El archivo está vacío"},
        "PRUEBA-tarea-1",
        {"error": True, "message": "Nombre de archivo no válido"},
    ]
    assert {"message", "task_ids", "expediente", "total_files"} <= set(cuerpo)
    assert isinstance(cuerpo["message"], str) and isinstance(cuerpo["total_files"], int)


# --- RF-05.22 y RF-21: guardado fallido y error interno -------------------------------------------------------------------

@pytest.mark.requisito("RF-05.22")
@pytest.mark.requisito("RF-21.7")
def test_guardado_fallido_y_error_interno_con_motivo_y_fila(cliente_api, sesion, usuario_gubernamental,
                                                            registro_de_datos, carpeta_archivos, encolado_interceptado,
                                                            parchar_instancia):
    """RF-05.22: un guardado que falla (la escritura lanza un error de disco con una ruta inventada) y un error interno
    (el guardado lanza otro tipo de error) figuran rechazados con su motivo y dejan cada uno una fila de rechazo, sin
    el texto de la excepción, la ruta ni el nombre; el válido sigue y no queda ningún archivo de los fallidos."""
    from app.services.documentos.file_management_service import file_management_service

    secreto = "/srv/PRUEBA_interna/PRUEBA_secreto.txt"
    falla_guardado, falla_interna = "PRUEBA_falla_guardado.txt", "PRUEBA_falla_interna.txt"
    unico_real = file_management_service._get_unique_filename
    guardar_real = file_management_service.guardar_archivo

    def _disco_lleno(directorio, nombre):
        if nombre == falla_guardado:
            raise OSError(f"disco lleno en {secreto}")
        return unico_real(directorio, nombre)

    async def _error_interno(file, tema):
        if file.filename == falla_interna:
            raise RuntimeError(f"fallo leyendo {secreto}")
        return await guardar_real(file, tema)

    # Siempre antes de escribir, como en la 004a. Se parchea la instancia: otra prueba que parchó la instancia con
    # `monkeypatch` deja al deshacer el método original en ella y taparía un parche de clase; `parchar_instancia`
    # devuelve la instancia a como estaba.
    parchar_instancia(file_management_service, "_get_unique_filename", _disco_lleno)
    parchar_instancia(file_management_service, "guardar_archivo", _error_interno)
    tema = tema_heredado(registro_de_datos)
    valido = documento_de_prueba()
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, tema, [(falla_guardado, b"PRUEBA a"), (valido.nombre, valido.contenido),
                                                   (falla_interna, b"PRUEBA b")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["task_ids"] == [
        {"error": True, "message": "No se pudo guardar el archivo"}, "PRUEBA-tarea-1",
        {"error": True, "message": "Error interno del servidor"}]
    assert cuerpo["aceptados"]["cantidad"] == 1 and cuerpo["total_files"] == 1
    assert cuerpo["rechazados"] == {"cantidad": 2, "archivos": [
        {"posicion": 1, "motivo": "no se pudo guardar el archivo"}, {"posicion": 3, "motivo": "error interno"}]}
    filas = _filas_desde(ultimo_id, usuario_gubernamental.cedula)
    assert sorted(f["texto"] for f in _rechazos(filas)) == [
        "Carga rechazada: error interno", "Carga rechazada: no se pudo guardar el archivo"]
    assert len(filas) == 3 and _iniciadas(filas)[0]["info"]["archivos_rechazados"] == 2
    registrado = [respuesta.text] + [f["texto"] + json.dumps(f["info"]) for f in filas]
    for contenido in registrado:
        assert secreto not in contenido and "PRUEBA_secreto" not in contenido and "disco lleno" not in contenido
        assert falla_guardado not in contenido and falla_interna not in contenido
    for fila in _rechazos(filas):
        assert "expediente" not in fila["info"] and tema not in json.dumps(fila["info"])
    assert _archivos_del_tema(carpeta_archivos, tema) == [valido.nombre]


# --- RF-05.22: todos rechazados y tema no válido --------------------------------------------------------------------------

@pytest.mark.requisito("RF-05.22")
def test_todos_rechazados_exito_sin_confirmacion(cliente_api, sesion, usuario_gubernamental, registro_de_datos,
                                                 carpeta_archivos, encolado_interceptado):
    """RF-05.22: si todos los archivos se rechazan (vacío y nombre no válido), la respuesta es un éxito con 0 aceptados,
    cada rechazado con su motivo, un mensaje que no dice que se enviaron archivos, ninguna tarea encolada, exactamente
    dos filas de rechazo y ninguna de carga iniciada."""
    tema = tema_heredado(registro_de_datos)
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, tema, [(NOMBRE_VACIO, b""), (NOMBRE_NO_VALIDO, b"PRUEBA contenido")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["aceptados"] == {"cantidad": 0, "tareas": []}
    assert cuerpo["rechazados"] == {"cantidad": 2, "archivos": [
        {"posicion": 1, "motivo": "archivo vacío"}, {"posicion": 2, "motivo": "nombre de archivo no válido"}]}
    assert cuerpo["total_files"] == 0
    assert cuerpo["message"] == MENSAJE_TODOS_RECHAZADOS and "enviado" not in cuerpo["message"]
    assert cuerpo["task_ids"] == [{"error": True, "message": "El archivo está vacío"},
                                  {"error": True, "message": "Nombre de archivo no válido"}]
    assert encolado_interceptado.pendientes == []
    filas = _filas_desde(ultimo_id, usuario_gubernamental.cedula)
    assert sorted(f["texto"] for f in filas) == [
        "Carga rechazada: archivo vacío", "Carga rechazada: nombre de archivo no válido"]
    assert _iniciadas(filas) == []
    assert _archivos_del_tema(carpeta_archivos, tema) == []


@pytest.mark.requisito("RF-05.22")
@pytest.mark.requisito("RF-06.20")
def test_tema_no_valido_sin_conteos(cliente_api, sesion, usuario_gubernamental, carpeta_archivos, encolado_interceptado):
    """RF-05.22 y RF-06.20: un tema que no sirve rechaza toda la carga con 400 y su aviso genérico, sin conteos de
    aceptados ni de rechazados, y deja solo la fila «tema no válido»."""
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, "a/b", [(NOMBRE_VACIO, b""), ("PRUEBA_otro.txt", b"PRUEBA contenido")])

    assert (respuesta.status_code, respuesta.json()) == (400, {"detail": "El tema indicado no es válido"})
    assert "aceptados" not in respuesta.text and "rechazados" not in respuesta.text
    assert [f["texto"] for f in _filas_desde(ultimo_id, usuario_gubernamental.cedula)] == [
        "Carga rechazada: tema no válido"]
    assert encolado_interceptado.pendientes == []


# --- RF-21: si la bitácora falla, la carga continúa -------------------------------------------------------------------------

@pytest.mark.requisito("RF-21.7")
@pytest.mark.requisito("RF-05.22")
def test_bitacora_que_falla_no_detiene_la_carga_mixta(cliente_api, sesion, usuario_gubernamental, registro_de_datos,
                                                      carpeta_archivos, encolado_interceptado, monkeypatch):
    """RF-21: si el registro en la bitácora falla, la carga mixta responde lo mismo (aceptados, rechazados y
    confirmación), se encola el válido y no queda ninguna fila."""
    from app.services.bitacora.bitacora_service import BitacoraService

    async def _falla(self, *args, **kwargs):
        raise Exception("falla simulada de la bitácora")

    monkeypatch.setattr(BitacoraService, "registrar", _falla)
    tema = tema_heredado(registro_de_datos)
    valido = documento_de_prueba()
    ultimo_id = _ultimo_id_de_bitacora()

    respuesta = cargar(cliente_api, sesion, tema, [(valido.nombre, valido.contenido), (NOMBRE_VACIO, b"")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["aceptados"]["cantidad"] == 1 and cuerpo["rechazados"]["cantidad"] == 1
    assert cuerpo["message"] == "1 archivo enviado a procesamiento"
    assert [p.id for p in encolado_interceptado.pendientes] == ["PRUEBA-tarea-1"]
    assert _filas_desde(ultimo_id, usuario_gubernamental.cedula) == []


# --- RF-05.23 (contenido): lo que la pantalla presenta ----------------------------------------------------------------------

@pytest.mark.requisito("RF-05.23")
def test_contenido_para_la_pantalla(cliente_api, sesion, registro_de_datos, notebook_de_prueba, carpeta_archivos,
                                    encolado_interceptado):
    """RF-05.23: desde Ingesta (un tema) y desde un notebook propio, lo que las pantallas presentan tal cual: el motivo
    de cada rechazado en español y sin el nombre, y la confirmación que cuenta solo los aceptados (singular, plural y,
    con todos rechazados, sin decir que se enviaron archivos)."""
    destinos = [tema_heredado(registro_de_datos), notebook_de_prueba.clave_interna]
    for tema in destinos:
        uno, otro = documento_de_prueba(), documento_de_prueba()

        mixta = cargar(cliente_api, sesion, tema, [(uno.nombre, uno.contenido), (NOMBRE_VACIO, b""),
                                                   (NOMBRE_NO_VALIDO, b"PRUEBA contenido")]).json()
        plural = cargar(cliente_api, sesion, tema, [(otro.nombre, otro.contenido), (documento_de_prueba().nombre, b"PRUEBA x"),
                                                    (NOMBRE_VACIO, b"")]).json()
        rechazados = cargar(cliente_api, sesion, tema, [(NOMBRE_VACIO, b""), (NOMBRE_NO_VALIDO, b"PRUEBA contenido")])

        assert mixta["message"] == "1 archivo enviado a procesamiento"
        assert plural["message"] == "2 archivos enviados a procesamiento" and plural["total_files"] == 2
        todos = rechazados.json()
        assert todos["message"] == MENSAJE_TODOS_RECHAZADOS and "enviado" not in todos["message"]
        for cuerpo in (mixta, plural, todos):
            assert cuerpo["aceptados"]["cantidad"] == len(cuerpo["aceptados"]["tareas"]) == cuerpo["total_files"]
            assert cuerpo["rechazados"]["cantidad"] == len(cuerpo["rechazados"]["archivos"])
            assert {a["motivo"] for a in cuerpo["rechazados"]["archivos"]} <= MOTIVOS
        _sin_rastros_del_nombre([json.dumps(mixta, ensure_ascii=False), rechazados.text], NOMBRE_NO_VALIDO)
        _sin_rastros_del_nombre([json.dumps(mixta, ensure_ascii=False), rechazados.text], NOMBRE_VACIO)


# --- RF-05.23 (CU-07 FA-01): imagen pegada o arrastrada sobre el chat del notebook ------------------------------------------

@pytest.mark.requisito("RF-05.23")
def test_imagen_pegada_en_el_notebook_llega_a_procesado(cliente_api, sesion, notebook_de_prueba, procesamiento_en_prueba,
                                                        htr_simulado):
    """RF-05.23: una imagen de nombre válido pegada o arrastrada sobre el chat de un notebook propio sube como cualquier
    otra carga: se acepta con la confirmación de un solo archivo, sin rechazados, pasa por el HTR (simulado, no llega
    a Tika) y llega a Procesado con sus fragmentos en el tema `NB-<id>`."""
    nombre = f"PRUEBA_pegada_{documento_de_prueba().nombre.split('_')[1].split('.')[0]}.png"
    frase = "la imagen inventada del notebook muestra una quebrada ficticia que desemboca en la laguna de los patos azules"
    htr_simulado.responder(f"PRUEBA texto simulado del HTR. {frase}. " * 6)
    tema = notebook_de_prueba.clave_interna

    respuesta = cargar(cliente_api, sesion, tema, [(nombre, b"PRUEBA bytes de imagen inventados")])

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["message"] == "1 archivo enviado a procesamiento"
    assert cuerpo["aceptados"] == {"cantidad": 1, "tareas": [{"posicion": 1, "id_tarea": "PRUEBA-tarea-1"}]}
    assert cuerpo["rechazados"] == {"cantidad": 0, "archivos": []}
    resultados = procesamiento_en_prueba.procesar()
    assert resultados["PRUEBA-tarea-1"].state == "SUCCESS"
    # El texto salió del HTR (una llamada con el nombre de la imagen) y el documento quedó Procesado con fragmentos.
    assert [l["nombre"] for l in htr_simulado.llamadas] == [nombre]
    id_documento = id_del_documento(nombre)
    assert id_documento is not None
    exigir_estado(id_documento, "Procesado")
    exigir_progreso("PRUEBA-tarea-1", "completado")
    assert contar_puntos(tema) > 0
