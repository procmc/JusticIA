"""Pruebas de T8 (spec 002, RA-02.7): usuarios `PRUEBA`, limpieza por prueba y conteo de residuos.

Unitarias: la lógica de `tests/soporte/datos.py` con SQL Server, Qdrant y Redis simulados por dobles que
registran lo que se les pide. Nada de esto abre una conexión real (el guardián de las unitarias lo vigila).
Lo que corre contra la base y la colección de pruebas reales vive en `tests/integracion/`.
"""
import json
import re
import tempfile
from pathlib import Path

import pytest

from tests.soporte import datos
from tests.soporte.nombres import NOMBRE_PRUEBAS, PREFIJO_DATOS
from tests.soporte.proteccion import AbortoPruebas

TABLAS_EN_ORDEN_DE_BORRADO = [
    "T_Bitacora", "T_Notebook", "T_Expediente_Documento", "T_Documento", "T_Expediente", "T_Usuario",
]
CATALOGOS = ["T_Rol", "T_Estado", "T_Estado_procesamiento", "T_Tipo_accion"]


# --- Dobles ---------------------------------------------------------------------------------------

class SQLSimulado:
    """Registra las sentencias que recibe; `contar` devuelve las cuentas que la prueba definió por tabla."""

    def __init__(self, cuentas=None):
        self.cuentas = dict(cuentas or {})
        self.borrados = []
        self.conteos = []
        self.error_en = None

    @staticmethod
    def _tabla(sentencia):
        return re.search(r"FROM\s+(\w+)", sentencia).group(1)

    def borrar(self, sentencia, parametros):
        tabla = self._tabla(sentencia)
        if tabla == self.error_en:
            raise RuntimeError(f"fallo simulado en {tabla}")
        self.borrados.append((tabla, sentencia, parametros))
        return 1

    def contar(self, sentencia, parametros):
        tabla = self._tabla(sentencia)
        self.conteos.append((tabla, sentencia, parametros))
        return self.cuentas.get(tabla, 0)

    @property
    def tablas_borradas(self):
        return [tabla for tabla, _, _ in self.borrados]

    @property
    def sentencias(self):
        return [s for _, s, _ in self.borrados] + [s for _, s, _ in self.conteos]


class PuntoSimulado:
    def __init__(self, id_, numero_expediente=None, sin_metadatos=False):
        self.id = id_
        self.payload = {} if sin_metadatos else {"metadata": {"numero_expediente": numero_expediente}}


class QdrantDePuntos:
    """Un Qdrant de mentira con puntos en memoria: `scroll`, `delete` y `count`, como los usa `datos`."""

    def __init__(self, puntos=()):
        self.puntos = list(puntos)
        self.colecciones_usadas = []
        self.borrados = []

    def scroll(self, collection_name, limit=10, offset=None, with_payload=True, with_vectors=False, **kwargs):
        self.colecciones_usadas.append(collection_name)
        return list(self.puntos), None

    def delete(self, collection_name, points_selector, wait=True, **kwargs):
        self.colecciones_usadas.append(collection_name)
        ids = set(points_selector.points)
        self.borrados.append(ids)
        self.puntos = [p for p in self.puntos if p.id not in ids]

    def count(self, collection_name, exact=True, **kwargs):
        self.colecciones_usadas.append(collection_name)
        return type("Cuenta", (), {"count": len(self.puntos)})()


class RedisDeMentira:
    def __init__(self, claves=0):
        self.claves = claves
        self.vaciado = 0

    def limpiar(self):
        self.vaciado += 1
        self.claves = 0

    def contar(self):
        return self.claves


def carpeta_de_pruebas(tmp_path: Path) -> Path:
    """Una carpeta que cumple la regla de las carpetas de la suite (bajo el directorio temporal, con su prefijo)."""
    carpeta = tmp_path / "servia_pruebas_unitaria"
    carpeta.mkdir()
    return carpeta


def un_destino(sql=None, qdrant=None, redis=None, carpeta=None, base=NOMBRE_PRUEBAS, coleccion=NOMBRE_PRUEBAS):
    return datos.Destino(
        base=base if sql is not None else None,
        coleccion=coleccion if qdrant is not None else None,
        carpeta=carpeta,
        borrar=sql.borrar if sql is not None else None,
        contar=sql.contar if sql is not None else None,
        qdrant=qdrant,
        limpiar_redis=redis.limpiar if redis is not None else None,
        claves_redis=redis.contar if redis is not None else None,
    )


# --- La contraseña de prueba ---------------------------------------------------------------------------

def test_la_contrasena_tiene_al_menos_8_caracteres_y_es_distinta_en_cada_llamada():
    """RA-02.7: al menos 8 caracteres, aleatoria y distinta cada vez (la suite no usa una contraseña fija)."""
    contrasenas = [datos.generar_contrasena() for _ in range(20)]
    assert all(len(c) >= 8 for c in contrasenas)
    assert len(set(contrasenas)) == 20


def test_el_repr_de_la_contrasena_no_la_muestra_pero_sigue_siendo_texto():
    """RA-02.7: la contraseña no sale en los mensajes de aserción ni en el `repr` del usuario; el inicio de sesión la envía como texto."""
    contrasena = datos.generar_contrasena()
    usuario = datos.UsuarioPrueba(
        cedula="PRUEBA000001", nombre_usuario="PRUEBA_u", correo="prueba1@prueba.invalid",
        contrasena=contrasena, rol=datos.ROL_ADMINISTRADOR,
    )

    assert contrasena not in repr(contrasena)
    assert contrasena not in repr(usuario)
    assert contrasena not in str(usuario)
    assert isinstance(contrasena, str)
    assert json.loads(json.dumps({"password": contrasena}))["password"] == contrasena  # el cuerpo del POST /auth/login


def test_la_contrasena_no_aparece_en_el_mensaje_de_una_asercion_fallida():
    """RA-02.7: pytest compara dos textos con su propio diff (`str`, no `repr`); el gancho de `datos` lo oculta."""
    contrasena = datos.generar_contrasena()
    mensajes = []
    with pytest.raises(AssertionError) as error:
        assert contrasena == "otra"
    mensajes.append(str(error.value))
    with pytest.raises(AssertionError) as error:
        assert "otra" == contrasena
    mensajes.append(str(error.value))
    with pytest.raises(AssertionError) as error:
        assert contrasena in "otra"
    mensajes.append(str(error.value))
    with pytest.raises(AssertionError) as error:
        assert contrasena != contrasena
    mensajes.append(str(error.value))

    for mensaje in mensajes:
        assert contrasena not in mensaje


def test_el_gancho_de_aserciones_solo_oculta_las_contrasenas():
    """Con otros valores pytest explica la aserción como siempre (el gancho devuelve `None`)."""
    assert datos.pytest_assertrepr_compare(None, "==", "uno", "dos") is None
    oculto = datos.pytest_assertrepr_compare(None, "==", datos.generar_contrasena(), "dos")
    assert oculto and "contraseña de prueba" in oculto[0]


# --- El registro y los archivos de la prueba ---------------------------------------------------------------

def test_crear_archivo_lo_escribe_directo_en_la_carpeta_y_lo_registra(tmp_path):
    """RA-02.7: el archivo de prueba lo escribe la suite (no `guardar_archivo`), con bytes inventados y el prefijo PRUEBA."""
    carpeta = carpeta_de_pruebas(tmp_path)
    registro = datos.Registro()

    ruta = registro.crear_archivo(carpeta, f"{PREFIJO_DATOS}_inventado.txt", "contenido inventado".encode())

    assert ruta.parent == carpeta and ruta.read_bytes() == b"contenido inventado"
    assert registro.archivos == [ruta]


def test_crear_archivo_exige_el_prefijo_para_poder_encontrarlo(tmp_path):
    carpeta = carpeta_de_pruebas(tmp_path)
    with pytest.raises(ValueError, match=PREFIJO_DATOS):
        datos.Registro().crear_archivo(carpeta, "contrato.txt", b"x")
    assert list(carpeta.iterdir()) == []


# --- La limpieza se niega con un destino que no es de pruebas ----------------------------------------------

@pytest.mark.parametrize("base", ["db_ServIA", "SERVIA_PRUEBAS", "master", ""])
def test_limpiar_se_niega_con_una_base_que_no_es_la_de_pruebas(base):
    """RA-02.7, RA-02.3: con otra base no se ejecuta ni una sentencia ni se toca nada más."""
    sql, qdrant, redis = SQLSimulado(), QdrantDePuntos([PuntoSimulado(1, "PRUEBA-x")]), RedisDeMentira(claves=3)

    with pytest.raises(AbortoPruebas, match="base"):
        datos.limpiar(un_destino(sql, qdrant, redis, base=base), datos.Registro())

    assert sql.borrados == [] and sql.conteos == []
    assert qdrant.borrados == [] and qdrant.colecciones_usadas == []
    assert redis.vaciado == 0 and redis.claves == 3


@pytest.mark.parametrize("coleccion", ["justicia_docs", "Servia_Pruebas", "servia_pruebas_2"])
def test_limpiar_se_niega_con_una_coleccion_que_no_es_la_de_pruebas(coleccion):
    """RA-02.7, RA-02.3: nunca borra puntos de `justicia_docs` ni de una colección de otro nombre."""
    sql, qdrant = SQLSimulado(), QdrantDePuntos([PuntoSimulado(1, "PRUEBA-x")])

    with pytest.raises(AbortoPruebas, match="colecci"):
        datos.limpiar(un_destino(sql, qdrant, coleccion=coleccion), datos.Registro())

    assert qdrant.borrados == [] and qdrant.colecciones_usadas == []
    assert sql.borrados == []


@pytest.mark.parametrize("carpeta", [
    Path("/app/uploads"),
    Path("/tmp/otra_carpeta"),
    Path("/tmp/servia_pruebas_../../app/uploads"),
    Path(tempfile.gettempdir()),
])
def test_limpiar_se_niega_con_una_carpeta_que_no_es_la_temporal_de_la_suite(carpeta):
    """RA-02.7, RA-02.5: nunca borra archivos de `uploads/` ni de una carpeta ajena a la suite."""
    sql = SQLSimulado()
    with pytest.raises(AbortoPruebas, match="carpeta"):
        datos.limpiar(un_destino(sql, carpeta=carpeta), datos.Registro())
    assert sql.borrados == []


def test_limpiar_no_borra_un_archivo_registrado_fuera_de_la_carpeta_de_pruebas(tmp_path):
    """Un archivo registrado que no está en la carpeta temporal (p. ej. en `uploads/`) hace abortar y no se toca."""
    carpeta = carpeta_de_pruebas(tmp_path)
    ajeno = tmp_path / "PRUEBA_ajeno.txt"
    ajeno.write_bytes(b"x")
    registro = datos.Registro()
    registro.archivos.append(ajeno)

    with pytest.raises(AbortoPruebas, match="fuera"):
        datos.limpiar(un_destino(carpeta=carpeta), registro)

    assert ajeno.exists()


# --- La limpieza con un destino de pruebas -------------------------------------------------------------------

def test_limpiar_borra_las_filas_en_orden_de_claves_foraneas_solo_con_el_prefijo_prueba():
    """RA-02.7: bitácora, notebooks, enlaces, documentos, temas y usuarios, en ese orden y solo lo que lleva `PRUEBA`."""
    sql = SQLSimulado()

    datos.limpiar(un_destino(sql), datos.Registro())

    assert sql.tablas_borradas == TABLAS_EN_ORDEN_DE_BORRADO
    for _, sentencia, parametros in sql.borrados:
        assert sentencia.lstrip().upper().startswith("DELETE FROM")
        assert "WHERE" in sentencia.upper()  # nunca un borrado de toda la tabla
        assert all(str(valor).replace("%", "") == PREFIJO_DATOS for valor in parametros.values())


def test_limpiar_no_toca_los_catalogos_de_las_migraciones():
    """RA-02.7: roles, estados y tipos de acción no se tocan (ninguna sentencia los nombra)."""
    sql = SQLSimulado()
    datos.limpiar(un_destino(sql), datos.Registro())
    for sentencia in sql.sentencias:
        for catalogo in CATALOGOS:
            assert not re.search(rf"\b{catalogo}\b", sentencia), f"{catalogo} aparece en: {sentencia}"


def test_limpiar_borra_los_puntos_registrados_y_los_del_prefijo_y_deja_los_demas():
    """RA-02.7: los puntos de la prueba (registrados o con tema `PRUEBA...`) se borran; los ajenos quedan para el conteo."""
    qdrant = QdrantDePuntos([
        PuntoSimulado(1, f"{PREFIJO_DATOS}-TEMA-1"),
        PuntoSimulado(2, "tema-ajeno"),
        PuntoSimulado(3, sin_metadatos=True),
    ])
    registro = datos.Registro()
    registro.registrar_punto(3)

    datos.limpiar(un_destino(qdrant=qdrant), registro)

    assert qdrant.borrados == [{1, 3}]
    assert [p.id for p in qdrant.puntos] == [2]
    assert set(qdrant.colecciones_usadas) == {NOMBRE_PRUEBAS}


def test_limpiar_borra_los_archivos_registrados_y_deja_los_demas(tmp_path):
    carpeta = carpeta_de_pruebas(tmp_path)
    registro = datos.Registro()
    propio = registro.crear_archivo(carpeta, f"{PREFIJO_DATOS}_propio.txt", b"a")
    ajeno = carpeta / f"{PREFIJO_DATOS}_sin_registrar.txt"
    ajeno.write_bytes(b"b")

    datos.limpiar(un_destino(carpeta=carpeta), registro)

    assert not propio.exists()
    assert ajeno.exists()  # lo que nadie registró queda a la vista: el conteo de residuos lo detecta


def test_limpiar_tolera_un_archivo_registrado_que_ya_no_existe(tmp_path):
    """El archivo pudo borrarse antes (p. ej. la fixture `carpeta_archivos` elimina su subcarpeta): no es un error."""
    carpeta = carpeta_de_pruebas(tmp_path)
    registro = datos.Registro()
    ruta = registro.crear_archivo(carpeta, f"{PREFIJO_DATOS}_x.txt", b"a")
    ruta.unlink()
    datos.limpiar(un_destino(carpeta=carpeta), registro)


def test_limpiar_vacia_el_redis_simulado():
    redis = RedisDeMentira(claves=5)
    datos.limpiar(un_destino(redis=redis), datos.Registro())
    assert redis.vaciado == 1 and redis.claves == 0


def test_limpiar_sin_servicios_reales_solo_limpia_redis_y_archivos(tmp_path):
    """Las unitarias no tienen SQL Server ni Qdrant: un destino sin ellos solo limpia lo que sí tienen."""
    carpeta = carpeta_de_pruebas(tmp_path)
    redis = RedisDeMentira(claves=2)
    registro = datos.Registro()
    ruta = registro.crear_archivo(carpeta, f"{PREFIJO_DATOS}_x.txt", b"a")

    datos.limpiar(un_destino(redis=redis, carpeta=carpeta), registro)

    assert redis.claves == 0 and not ruta.exists()


def test_si_un_paso_de_la_limpieza_falla_los_demas_se_ejecutan_y_el_error_lo_nombra(tmp_path):
    """Un fallo en una tabla no deja sin limpiar el Redis ni los archivos."""
    carpeta = carpeta_de_pruebas(tmp_path)
    sql, redis = SQLSimulado(), RedisDeMentira(claves=1)
    sql.error_en = "T_Documento"
    registro = datos.Registro()
    ruta = registro.crear_archivo(carpeta, f"{PREFIJO_DATOS}_x.txt", b"a")

    with pytest.raises(AbortoPruebas, match="T_Documento"):
        datos.limpiar(un_destino(sql, redis=redis, carpeta=carpeta), registro)

    assert "T_Usuario" in sql.tablas_borradas  # siguió después del fallo
    assert redis.claves == 0 and not ruta.exists()


# --- El conteo de residuos -------------------------------------------------------------------------------------

def test_sin_residuos_el_conteo_da_cero(tmp_path):
    carpeta = carpeta_de_pruebas(tmp_path)
    residuos = datos.contar_residuos(un_destino(SQLSimulado(), QdrantDePuntos(), RedisDeMentira(), carpeta))

    assert residuos.total == 0
    assert not residuos.hay
    assert residuos.filas == {tabla: 0 for tabla in TABLAS_EN_ORDEN_DE_BORRADO}
    assert residuos.puntos == 0 and residuos.archivos == [] and residuos.claves_redis == 0


def test_los_residuos_se_cuentan_y_se_nombran(tmp_path):
    """RA-02.7: filas por tabla, puntos de la colección (todos: es de uso exclusivo), archivos y claves de Redis."""
    carpeta = carpeta_de_pruebas(tmp_path)
    (carpeta / "PRUEBA_olvidado.txt").write_bytes(b"x")
    sql = SQLSimulado({"T_Usuario": 2, "T_Bitacora": 3})
    qdrant = QdrantDePuntos([PuntoSimulado(1, "tema-ajeno")])  # sin prefijo: igual es un residuo
    redis = RedisDeMentira(claves=4)

    residuos = datos.contar_residuos(un_destino(sql, qdrant, redis, carpeta))

    assert residuos.hay
    assert residuos.filas["T_Usuario"] == 2 and residuos.filas["T_Bitacora"] == 3
    assert residuos.puntos == 1
    assert [Path(a).name for a in residuos.archivos] == ["PRUEBA_olvidado.txt"]
    assert residuos.claves_redis == 4
    assert residuos.total == 2 + 3 + 1 + 1 + 4
    texto = residuos.texto()
    for esperado in ("T_Usuario", "T_Bitacora", "puntos", "PRUEBA_olvidado.txt", "Redis"):
        assert esperado in texto


def test_el_conteo_de_residuos_se_niega_con_un_destino_ajeno():
    sql = SQLSimulado()
    with pytest.raises(AbortoPruebas):
        datos.contar_residuos(un_destino(sql, base="db_ServIA"))
    assert sql.conteos == []


def test_el_resumen_de_residuos_dice_ninguno_cuando_no_quedo_nada(monkeypatch):
    monkeypatch.setitem(datos._estado, "residuos", datos.Residuos(filas={"T_Usuario": 0}))
    monkeypatch.setitem(datos._estado, "conteo_fallido", None)
    assert not datos.hay_problema_de_residuos()
    assert datos.lineas_de_residuos() == ["Residuos de datos de prueba al cerrar la sesión: ninguno"]


def test_el_resumen_de_residuos_falla_y_nombra_lo_que_quedo(monkeypatch):
    monkeypatch.setitem(datos._estado, "residuos", datos.Residuos(filas={"T_Usuario": 2}, puntos=1))
    monkeypatch.setitem(datos._estado, "conteo_fallido", None)
    assert datos.hay_problema_de_residuos()
    [linea] = datos.lineas_de_residuos()
    assert linea.startswith("FALLA") and "T_Usuario: 2" in linea and "puntos de la colección de Qdrant: 1" in linea


def test_si_el_conteo_de_residuos_mismo_falla_el_resumen_lo_dice_como_un_fallo(monkeypatch):
    """RA-02.7: no poder contar no es «no quedó nada»."""
    monkeypatch.setitem(datos._estado, "residuos", None)
    monkeypatch.setitem(datos._estado, "conteo_fallido", "OperationalError")
    assert datos.hay_problema_de_residuos()
    [linea] = datos.lineas_de_residuos()
    assert linea.startswith("FALLA") and "OperationalError" in linea


def test_sin_conteo_no_hay_lineas_ni_problema(monkeypatch):
    """Una corrida que no llegó a contar (por ejemplo, `--collect-only`) no imprime nada sobre residuos."""
    monkeypatch.setitem(datos._estado, "residuos", None)
    monkeypatch.setitem(datos._estado, "conteo_fallido", None)
    assert not datos.hay_problema_de_residuos()
    assert datos.lineas_de_residuos() == []


# --- Los catálogos de las migraciones --------------------------------------------------------------------------------

def test_contar_catalogos_cuenta_los_cuatro_catalogos_sin_modificar_nada():
    sql = SQLSimulado({"T_Rol": 2, "T_Estado": 2, "T_Estado_procesamiento": 3, "T_Tipo_accion": 15})
    assert datos.contar_catalogos(sql.contar) == {
        "T_Rol": 2, "T_Estado": 2, "T_Estado_procesamiento": 3, "T_Tipo_accion": 15,
    }
    assert sql.borrados == []


def test_comparar_catalogos_detecta_lo_que_falta_o_sobra():
    antes = {"T_Rol": 2, "T_Estado": 2, "T_Estado_procesamiento": 3, "T_Tipo_accion": 15}
    assert datos.comparar_catalogos(antes, dict(antes)) == []
    diferencias = datos.comparar_catalogos(antes, {**antes, "T_Rol": 1, "T_Tipo_accion": 16})
    assert len(diferencias) == 2
    assert "T_Rol" in diferencias[0] and "T_Tipo_accion" in diferencias[1]
