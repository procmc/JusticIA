"""Baja lógica de la fuente del notebook, parte de integración (spec 009b, cambio GG1; RF-19.111, RN-01.101).

Con SQL Server real del entorno aislado. Datos inventados (prefijo `PRUEBA`).
"""
import pytest

from tests.integracion.conftest import _consultar


@pytest.mark.requisito("RF-19.111")
@pytest.mark.requisito("RN-01.101")
def test_migracion_baja_logica_columnas_y_clave_foranea():
    """RF-19.111, RN-01.101: T_Documento tiene CF_Fecha_baja (fecha y hora) y CN_Id_usuario_baja (cédula, 20), ambas con
    NULL permitido, y la segunda con clave foránea a T_Usuario; el modelo las declara igual."""
    from app.db.models.documento import T_Documento

    columnas = _consultar(
        "SELECT COLUMN_NAME, IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'T_Documento' AND COLUMN_NAME IN ('CF_Fecha_baja', 'CN_Id_usuario_baja') ORDER BY COLUMN_NAME")
    assert [tuple(fila) for fila in columnas] == [
        ("CF_Fecha_baja", "YES", "datetime", None),
        ("CN_Id_usuario_baja", "YES", "varchar", 20),
    ]
    assert T_Documento.__table__.c.CF_Fecha_baja.nullable is True
    assert T_Documento.__table__.c.CN_Id_usuario_baja.nullable is True

    claves = _consultar(
        "SELECT COUNT(*) FROM sys.foreign_key_columns fkc "
        "JOIN sys.columns c ON c.object_id = fkc.parent_object_id AND c.column_id = fkc.parent_column_id "
        "WHERE fkc.parent_object_id = OBJECT_ID('T_Documento') AND c.name = 'CN_Id_usuario_baja' "
        "AND fkc.referenced_object_id = OBJECT_ID('T_Usuario')")
    assert claves[0][0] == 1


@pytest.mark.requisito("RF-19.111")
def test_los_documentos_existentes_quedan_activos():
    """RF-19.111: ninguna fila de T_Documento anterior al cambio queda con baja (todas nulas)."""
    con_baja = _consultar("SELECT COUNT(*) FROM T_Documento WHERE CF_Fecha_baja IS NOT NULL OR CN_Id_usuario_baja IS NOT NULL")
    assert con_baja[0][0] == 0


# --- T10: el repositorio marca la baja y todas sus consultas ignoran lo quitado (RF-19.111, RF-19.113, RF-19.114) ----------

import uuid
from datetime import datetime, timedelta

from tests.soporte.nombres import PREFIJO_DATOS


def _tema_con_dos_documentos():
    """Un tema `PRUEBA` con un documento activo y otro que luego se quita; los dos Procesado y con ruta. Devuelve los datos que
    usan las pruebas. La limpieza por prueba borra todo lo que lleva el prefijo."""
    from app.db.database import SessionLocal
    from app.db.models import T_Documento, T_Estado_procesamiento, T_Expediente

    sufijo = uuid.uuid4().hex[:8]
    tema_numero = f"{PREFIJO_DATOS} baja {sufijo}"
    with SessionLocal() as db:
        procesado = db.query(T_Estado_procesamiento).filter(T_Estado_procesamiento.CT_Nombre_estado == "Procesado").one()
        tema = T_Expediente(CT_Num_expediente=tema_numero)
        documentos = {}
        for clave in ("activo", "quitado"):
            nombre = f"{PREFIJO_DATOS}_{clave}_{sufijo}.txt"
            documento = T_Documento(CT_Nombre_archivo=nombre, CT_Tipo_archivo="txt", CN_Id_estado=procesado.CN_Id_estado,
                                    CT_Ruta_archivo=f"uploads/{tema_numero}/{nombre}")
            tema.documentos.append(documento)
            documentos[clave] = documento
        db.add(tema)
        db.commit()
        datos = {"tema": tema_numero, "id_tema": tema.CN_Id_expediente,
                 "activo": (documentos["activo"].CN_Id_documento, documentos["activo"].CT_Nombre_archivo),
                 "quitado": (documentos["quitado"].CN_Id_documento, documentos["quitado"].CT_Nombre_archivo)}
    datos["usuario"] = _consultar("SELECT TOP 1 CN_Id_usuario FROM T_Usuario ORDER BY CN_Id_usuario")[0][0]
    return datos


def _quitar(datos):
    from app.db.database import SessionLocal
    from app.repositories.documento_repository import DocumentoRepository

    repo = DocumentoRepository()
    with SessionLocal() as db:
        documento = repo.obtener_por_id(db, datos["quitado"][0])
        repo.dar_de_baja(db, documento, datos["usuario"])


@pytest.mark.requisito("RF-19.111")
def test_dar_de_baja_marca_la_fila_sin_borrarla():
    """RF-19.111: la baja guarda fecha y hora y quién la quitó, y conserva nombre, tipo y la relación con el tema; el documento
    activo no cambia."""
    datos = _tema_con_dos_documentos()
    antes = datetime.utcnow() - timedelta(minutes=5)
    _quitar(datos)
    id_quitado, nombre_quitado = datos["quitado"]

    fila = _consultar(f"SELECT CT_Nombre_archivo, CT_Tipo_archivo, CF_Fecha_baja, CN_Id_usuario_baja FROM T_Documento "
                      f"WHERE CN_Id_documento = {id_quitado}")
    assert len(fila) == 1
    nombre, tipo, fecha, usuario = fila[0]
    assert (nombre, tipo, usuario) == (nombre_quitado, "txt", datos["usuario"])
    assert antes <= fecha <= datetime.utcnow() + timedelta(minutes=5)
    unidas = _consultar(f"SELECT COUNT(*) FROM T_Expediente_Documento WHERE CN_Id_documento = {id_quitado}")
    assert unidas[0][0] == 1
    activo = _consultar(f"SELECT CF_Fecha_baja, CN_Id_usuario_baja FROM T_Documento WHERE CN_Id_documento = {datos['activo'][0]}")
    assert tuple(activo[0]) == (None, None)


@pytest.mark.requisito("RF-19.113")
def test_obtener_por_id_ignora_al_quitado_salvo_que_se_pida():
    from app.db.database import SessionLocal
    from app.repositories.documento_repository import DocumentoRepository

    datos = _tema_con_dos_documentos()
    _quitar(datos)
    repo = DocumentoRepository()
    with SessionLocal() as db:
        assert repo.obtener_por_id(db, datos["activo"][0]) is not None
        assert repo.obtener_por_id(db, datos["quitado"][0]) is None
        assert repo.obtener_por_id(db, datos["quitado"][0], incluir_quitados=True).esta_quitado is True


def _nombres_por_id(db, ids):
    from app.db.models import T_Documento

    return {d.CT_Nombre_archivo for d in db.query(T_Documento).filter(T_Documento.CN_Id_documento.in_(list(ids))).all()}


# Cada consulta pública del repositorio que lee documentos, vista como «los nombres de archivo del tema de la prueba que devuelve».
def _por_expediente(repo, db, d):
    from app.db.models import T_Expediente
    tema = db.query(T_Expediente).filter(T_Expediente.CN_Id_expediente == d["id_tema"]).one()
    return {x.CT_Nombre_archivo for x in repo.listar_por_expediente(db, tema)}


def _por_expediente_procesados(repo, db, d):
    from app.db.models import T_Expediente
    tema = db.query(T_Expediente).filter(T_Expediente.CN_Id_expediente == d["id_tema"]).one()
    return {x.CT_Nombre_archivo for x in repo.listar_por_expediente(db, tema, solo_procesados=True)}


def _rutas_de_carpeta(repo, db, d):
    ids = {i for i, _ in repo.listar_rutas_de_carpeta(db, d["tema"])}
    return _nombres_por_id(db, ids)


def _procesados_con_temas(repo, db, d):
    return _nombres_por_id(db, {i for i, t in repo.listar_procesados_con_temas(db) if t == d["tema"]})


def _procesados_de_temas(repo, db, d):
    return _nombres_por_id(db, {fila[0] for fila in repo.listar_procesados_de_temas(db, [d["tema"]])})


def _ids_procesados(repo, db, d):
    return _nombres_por_id(db, repo.obtener_ids_procesados(db) & {d["activo"][0], d["quitado"][0]})


def _por_nombres(repo, db, d):
    return set(repo.listar_por_expediente_y_nombres(db, d["tema"], solo_procesados=False)) | \
        set(repo.listar_por_expediente_y_nombres(db, d["tema"], solo_procesados=True))


def _esta_procesado(repo, db, d):
    return {n for _, n in (d["activo"], d["quitado"]) if repo.verificar_esta_procesado(db, d["tema"], n)}


CONSULTAS = [_por_expediente, _por_expediente_procesados, _rutas_de_carpeta, _procesados_con_temas, _procesados_de_temas,
             _ids_procesados, _por_nombres, _esta_procesado]


@pytest.mark.requisito("RF-19.113")
@pytest.mark.requisito("RF-19.114")
@pytest.mark.parametrize("consulta", CONSULTAS, ids=lambda c: c.__name__)
def test_ninguna_consulta_del_repositorio_devuelve_un_documento_quitado(consulta):
    """RF-19.113: el quitado no sale en ninguna consulta del repositorio; el activo del mismo tema sí (control de la prueba)."""
    from app.db.database import SessionLocal
    from app.repositories.documento_repository import DocumentoRepository

    datos = _tema_con_dos_documentos()
    repo = DocumentoRepository()
    with SessionLocal() as db:
        antes = consulta(repo, db, datos)
        assert {datos["activo"][1], datos["quitado"][1]} <= antes, "la consulta debe ver los dos antes de la baja"
    _quitar(datos)
    with SessionLocal() as db:
        despues = consulta(repo, db, datos)
    assert datos["activo"][1] in despues
    assert datos["quitado"][1] not in despues
