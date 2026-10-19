"""Detalle de un registro de carga para la bitácora completa (spec 004, tarea 9c, bloque F; RF-22.1).

Prueba las funciones puras de `detalle_carga.py`, sin servicios:
- `clasificar_causa`: la regla de la spec (Definiciones) con su precedencia; el texto de la excepción nunca sale.
- `armar_detalle_carga`: el nombre visible del tipo y los datos en el orden de la tabla de RF-22.1, sin los valores de
  relleno ni los datos técnicos.
- `hora_de_costa_rica`: la hora guardada en UTC se muestra en UTC-6 (Andrés, 15/10/2026).

Son regresiones: se escribieron contra la spec antes de crear el módulo y se vieron fallar.
"""
from datetime import datetime

import pytest

from app.services.bitacora.detalle_carga import armar_detalle_carga, clasificar_causa, hora_de_costa_rica

FECHA_UTC = datetime(2026, 10, 15, 3, 30, 5)  # en Costa Rica: 14/10/2026 21:30:05
FECHA_CR = "14/10/2026 21:30:05"

FORMATO_O_TAMANO = "formato o tamaño no permitido"
NO_SE_PUDO_EXTRAER = "no se pudo extraer el texto"
SERVICIO_NO_DISPONIBLE = "servicio de procesamiento no disponible"
NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA = "no se pudo guardar para la búsqueda"
ERROR_INTERNO = "error interno"


def _datos(detalle: dict) -> list:
    return [(d["etiqueta"], d["valor"]) for d in detalle["datos"]]


def _etiquetas(detalle: dict) -> list:
    return [d["etiqueta"] for d in detalle["datos"]]


# --- clasificar_causa -----------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
@pytest.mark.parametrize("crudo, esperada", [
    # 1. Formato o tamaño (empieza por, o contiene «excede el límite»; sin distinguir mayúsculas)
    ("Formato no permitido: .exe", FORMATO_O_TAMANO),
    ("TIPO MIME NO PERMITIDO: application/x-msdownload", FORMATO_O_TAMANO),
    ("Archivo demasiado grande (2 GB)", FORMATO_O_TAMANO),
    ("Extensión '.exe' no permitida", FORMATO_O_TAMANO),
    ("Tipo MIME 'text/x' no permitido", FORMATO_O_TAMANO),
    ("El archivo excede el límite de 1 GB", FORMATO_O_TAMANO),
    # 2. Extracción: sin señal de servicio caído → no se pudo extraer
    ("Error extrayendo texto: documento dañado", NO_SE_PUDO_EXTRAER),
    ("No se pudo extraer texto del archivo", NO_SE_PUDO_EXTRAER),
    ("Error transcribiendo audio: formato raro", NO_SE_PUDO_EXTRAER),
    ("No se pudo transcribir el audio", NO_SE_PUDO_EXTRAER),
    ("No se pudo reconocer el manuscrito", NO_SE_PUDO_EXTRAER),
    # 2. Extracción con señal de servicio caído
    ("Error extrayendo texto: servicio no disponible", SERVICIO_NO_DISPONIBLE),
    ("Error transcribiendo audio: timeout", SERVICIO_NO_DISPONIBLE),
    ("No se pudo extraer texto: timed out", SERVICIO_NO_DISPONIBLE),
    ("No se pudo transcribir: Connection refused", SERVICIO_NO_DISPONIBLE),
    ("No se pudo reconocer el manuscrito: error de conexión", SERVICIO_NO_DISPONIBLE),
    ("Error extrayendo texto: falló después de 3 intentos", SERVICIO_NO_DISPONIBLE),
    # 3. Guardado para la búsqueda
    ("Fallo al escribir en Qdrant", NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA),
    ("Error del vector store", NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA),
    ("Error generando embeddings", NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA),
    ("La collection no existe", NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA),
    ("No se encontró la colección", NO_SE_PUDO_GUARDAR_PARA_BUSQUEDA),
])
def test_clasifica_cada_regla(crudo, esperada):
    """RF-22.1: cada regla de la clasificación del fallo del procesamiento da su causa, sin distinguir mayúsculas."""
    assert clasificar_causa(crudo) == esperada


@pytest.mark.requisito("RF-22.1")
def test_precedencia_extraccion_con_conexion():
    """RF-22.1: gana la primera regla que se cumple. Un fallo de extracción que además menciona la conexión es «servicio
    no disponible» (regla 2), y uno de formato que menciona la conexión sigue siendo de formato (regla 1)."""
    assert clasificar_causa("Error extrayendo texto: connection reset") == SERVICIO_NO_DISPONIBLE
    assert clasificar_causa("Formato no permitido: connection") == FORMATO_O_TAMANO
    assert clasificar_causa("Error de conexión con el servidor") == ERROR_INTERNO  # sin regla 2: no es de extracción


@pytest.mark.requisito("RF-22.1")
def test_nombre_con_vector_dentro_de_extraccion():
    """RF-22.1: un fallo de extracción cuyo texto menciona «vector» (p. ej. en el nombre del archivo) sigue siendo de
    extracción y no de guardado: la regla 2 va antes que la 3."""
    assert clasificar_causa("Error extrayendo texto: PRUEBA_vector.pdf está dañado") == NO_SE_PUDO_EXTRAER
    assert clasificar_causa("No se pudo extraer texto de PRUEBA_qdrant.docx") == NO_SE_PUDO_EXTRAER


@pytest.mark.requisito("RF-22.1")
@pytest.mark.parametrize("crudo", [None, "", "   ", "Algo que no encaja en ninguna regla", "Timeout procesando PRUEBA.txt"])
def test_no_reconocido_y_vacio_son_error_interno(crudo):
    """RF-22.1: sin error guardado, o con un texto que no encaja en ninguna regla, la causa es «error interno»; el texto
    crudo nunca se devuelve."""
    causa = clasificar_causa(crudo)
    assert causa == ERROR_INTERNO
    if crudo:
        assert crudo not in causa


# --- armar_detalle_carga --------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
@pytest.mark.parametrize("info, tipo, datos", [
    ({"fase": "iniciado", "expediente": "99-000001-0001-PE", "archivo": "2 archivo(s)", "task_id": "a,b",
      "archivos_aceptados": 2, "archivos_rechazados": 1},
     "Carga iniciada",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivos aceptados", "2"),
      ("Archivos rechazados", "1")]),
    ({"fase": "inicio", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt", "task_id": "t1"},
     "Inicio del procesamiento",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt")]),
    ({"fase": "vectorstore_exitoso", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt", "documento_id": 7,
      "num_chunks": 4, "num_vectores": 4, "collection": "documentos"},
     "Documento almacenado",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt"), ("Documento", "7"),
      ("Fragmentos", "4")]),
    ({"fase": "completado", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt", "task_id": "t1",
      "documento_id": "t1"},
     "Procesamiento terminado",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt")]),
    ({"fase": "error", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt", "task_id": "t1",
      "error_details": "Error extrayendo texto: documento dañado"},
     "Error de procesamiento",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt"),
      ("Causa", NO_SE_PUDO_EXTRAER)]),
    ({"motivo": "archivo vacío", "error": "carga rechazada", "tipo_error": "validacion"},
     "Carga rechazada",
     [("Fecha y hora", FECHA_CR), ("Motivo", "archivo vacío")]),
    ({"fase": "cancelado", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt", "task_id": "t1"},
     "Cancelación",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt")]),
    ({"fase": "error_cancelacion", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt"},
     "Error de cancelación",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt")]),
    ({"fase": "otra_cosa", "expediente": "99-000001-0001-PE", "archivo": "PRUEBA_a.txt"},
     "Otra fase",
     [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Archivo", "PRUEBA_a.txt")]),
])
def test_detalle_por_tipo_en_orden(info, tipo, datos):
    """RF-22.1: cada tipo de registro de carga entrega su nombre visible y sus datos con etiqueta en español, en el
    orden de la tabla, y ninguno de los datos técnicos (tarea, colección, vectores, fase)."""
    detalle = armar_detalle_carga(info, FECHA_UTC)

    assert detalle["tipo"] == tipo
    assert _datos(detalle) == datos
    assert "Expediente" not in _etiquetas(detalle)


@pytest.mark.requisito("RF-22.1")
def test_motivo_fuera_de_la_lista_cerrada_es_error_interno():
    """RF-22.1: el motivo de un rechazo se muestra solo si es uno de la lista cerrada; si no, «error interno»."""
    for motivo in ("tema no válido", "nombre de archivo no válido", "archivo vacío", "no se pudo guardar el archivo",
                   "error interno"):
        assert ("Motivo", motivo) in _datos(armar_detalle_carga({"motivo": motivo}, FECHA_UTC))
    desconocido = armar_detalle_carga({"motivo": r"fallo en C:\datos\PRUEBA_x.pdf"}, FECHA_UTC)
    assert ("Motivo", "error interno") in _datos(desconocido)
    assert "PRUEBA_x" not in str(desconocido)


@pytest.mark.requisito("RF-22.1")
def test_relleno_omitido():
    """RF-22.1: un tema «N/A» o vacío y un archivo «Error general» o «Task <id>» son relleno y se omiten; los rechazados
    se muestran solo si son más de cero. La cancelación queda con solo Fecha y hora; el error general de la carga, con
    Tema, Fecha y hora y la causa «error interno»."""
    cancelacion = armar_detalle_carga(
        {"fase": "cancelado", "expediente": "N/A", "archivo": "Task abc-123", "task_id": "abc-123"}, FECHA_UTC)
    assert cancelacion["tipo"] == "Cancelación" and _datos(cancelacion) == [("Fecha y hora", FECHA_CR)]

    error_de_cancelacion = armar_detalle_carga(
        {"fase": "error_cancelacion", "expediente": "", "archivo": "Task abc-123"}, FECHA_UTC)
    assert _datos(error_de_cancelacion) == [("Fecha y hora", FECHA_CR)]

    general = armar_detalle_carga(
        {"fase": "error", "expediente": "99-000001-0001-PE", "archivo": "Error general", "task_id": "N/A"}, FECHA_UTC)
    assert general["tipo"] == "Error de procesamiento"
    assert _datos(general) == [("Tema", "99-000001-0001-PE"), ("Fecha y hora", FECHA_CR), ("Causa", ERROR_INTERNO)]

    sin_rechazados = armar_detalle_carga(
        {"fase": "iniciado", "expediente": "99-000001-0001-PE", "archivos_aceptados": 3, "archivos_rechazados": 0},
        FECHA_UTC)
    assert "Archivos rechazados" not in _etiquetas(sin_rechazados)
    assert ("Archivos aceptados", "3") in _datos(sin_rechazados)

    anterior = armar_detalle_carga({"fase": "iniciado", "expediente": "99-000001-0001-PE"}, FECHA_UTC)
    assert _etiquetas(anterior) == ["Tema", "Fecha y hora"]  # filas anteriores sin los conteos: se omiten


@pytest.mark.requisito("RF-22.1")
def test_info_ausente_o_danada_no_falla():
    """RF-22.1: una fila sin información adicional (o con algo que no es un diccionario) no rompe la consulta: es «Otra
    fase» con solo Fecha y hora."""
    for info in (None, {}, [], "texto"):
        detalle = armar_detalle_carga(info, FECHA_UTC)
        assert detalle["tipo"] == "Otra fase" and _datos(detalle) == [("Fecha y hora", FECHA_CR)]


# --- hora_de_costa_rica ---------------------------------------------------------------------------------------------------

@pytest.mark.requisito("RF-22.1")
def test_hora_de_costa_rica():
    """RF-22.1 (Andrés, 15/10 = B): la hora UTC guardada se muestra seis horas antes, «dd/mm/aaaa hh:mm:ss», con el cambio
    de día y de año cuando corresponde."""
    assert hora_de_costa_rica(FECHA_UTC) == FECHA_CR
    assert hora_de_costa_rica(datetime(2026, 1, 1, 5, 59, 59)) == "31/12/2025 23:59:59"
    assert hora_de_costa_rica(datetime(2026, 10, 15, 6, 0, 0)) == "15/10/2026 00:00:00"
    assert hora_de_costa_rica(None) == ""
