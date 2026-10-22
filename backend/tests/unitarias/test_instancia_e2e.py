"""Pruebas de T1 y T3 (spec 005a, RA-02.41, RA-02.42, RA-02.43 y RA-02.49): la instancia de pruebas de extremo a extremo.

La instancia es un segundo proceso del backend con su propia base y colección (`servia_pruebas_e2e`). Estas pruebas
cubren la lógica que se puede comprobar sin arrancarla: la protección de los dos nombres, la configuración, la carpeta
temporal, la ausencia del control en el backend de desarrollo y el vigilante de inactividad. Ninguna abre conexiones:
el arranque real se comprueba a mano (plan-005a, §12).
"""
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.instancia_e2e import __main__ as lanzador
from tests.instancia_e2e import configuracion as cfg_e2e
from tests.instancia_e2e import control
from tests.instancia_e2e import simulados_e2e
from tests.instancia_e2e.simulados_e2e import LIMITE_INACTIVIDAD_SEGUNDOS, RegistroContrasenas, Vigilante
from tests.soporte import configuracion, proteccion, simulados
from tests.soporte.nombres import NOMBRE_PRUEBAS, NOMBRE_PRUEBAS_E2E
from tests.soporte.proteccion import AbortoPruebas, exigir_nombre_pruebas

RAIZ_BACKEND = Path(__file__).resolve().parents[2]

# Solo las seis credenciales de desarrollo que la suite toma del entorno real.
DESARROLLO = {nombre: f"valor-{nombre.lower()}" for nombre in configuracion.VARIABLES_DESARROLLO}

URL_BASE = "mssql+pyodbc://usuario:clave%21@servidor-falso:1433/{base}?driver=Driver+Falso&TrustServerCertificate=yes"
ENTORNO_CORREO_INVENTADO = {"EMAIL_HOST": "smtp.correo.invalid"}


@pytest.fixture
def nombre_e2e():
    """Pone `servia_pruebas_e2e` como nombre activo y devuelve el de pytest al terminar, falle o no la prueba."""
    proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS_E2E)
    try:
        yield
    finally:
        proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS)


def _modulo_config(base=NOMBRE_PRUEBAS_E2E, coleccion=NOMBRE_PRUEBAS_E2E, redis="redis://redis.invalid:6379",
                   ollama="http://ollama.invalid:11434", htr="http://htr.invalid:9100"):
    """Un sustituto de `app.config.config` con los valores que importaría el sistema."""
    return SimpleNamespace(DATABASE_URL=URL_BASE.format(base=base), QDRANT_COLLECTION_NAME=coleccion,
                           REDIS_URL=redis, OLLAMA_BASE_URL=ollama, HTR_SERVER_URL=htr)


# --- RA-02.41: configuración de la instancia ------------------------------------------------------------

def test_configuracion_e2e_nombres_y_servicios_invalidos(nombre_e2e):
    """RA-02.41, RNF-09.40: nombres `servia_pruebas_e2e`, servicios `*.invalid`, modo sin conexión; todo otro valor aborta."""
    configuracion_e2e = cfg_e2e.construir_configuracion_e2e(DESARROLLO)

    assert configuracion_e2e["SQL_SERVER_DATABASE"] == NOMBRE_PRUEBAS_E2E
    assert configuracion_e2e["QDRANT_COLLECTION_NAME"] == NOMBRE_PRUEBAS_E2E
    assert NOMBRE_PRUEBAS not in (configuracion_e2e["SQL_SERVER_DATABASE"], configuracion_e2e["QDRANT_COLLECTION_NAME"])
    for variable, valor in {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "LANGSMITH_TRACING": "false",
                            "PYTHONDONTWRITEBYTECODE": "1"}.items():
        assert configuracion_e2e[variable] == valor
    for variable in ("REDIS_URL", "OLLAMA_BASE_URL", "HTR_SERVER_URL"):
        assert configuracion._host_de(configuracion_e2e[variable]).endswith(".invalid"), variable
    assert configuracion_e2e["EMAIL_HOST"].endswith(".invalid")
    # De desarrollo solo salen las seis credenciales permitidas.
    for variable in configuracion.VARIABLES_DESARROLLO:
        assert configuracion_e2e[variable] == DESARROLLO[variable]

    # El valor efectivo que tomó el sistema también se valida contra el nombre activo.
    configuracion.validar_valores_efectivos(_modulo_config(), ENTORNO_CORREO_INVENTADO)
    for malo in (_modulo_config(base=NOMBRE_PRUEBAS), _modulo_config(base="db_ServIA"),
                 _modulo_config(coleccion=NOMBRE_PRUEBAS), _modulo_config(coleccion="justicia_docs")):
        with pytest.raises(AbortoPruebas):
            configuracion.validar_valores_efectivos(malo, ENTORNO_CORREO_INVENTADO)
    for malo in (_modulo_config(redis="redis://redis:6379"), _modulo_config(ollama="http://ollama:11434"),
                 _modulo_config(htr="http://servidor-htr:9100")):
        with pytest.raises(AbortoPruebas):
            configuracion.validar_valores_efectivos(malo, ENTORNO_CORREO_INVENTADO)
    with pytest.raises(AbortoPruebas):
        configuracion.validar_valores_efectivos(_modulo_config(), {"EMAIL_HOST": "sandbox.smtp.mailtrap.io"})


def test_configuracion_e2e_exige_el_nombre_activo_e2e():
    """RA-02.41: sin haber fijado el nombre e2e (la corrida de pytest), no se arma la configuración de la instancia."""
    assert proteccion.nombre_activo() == NOMBRE_PRUEBAS
    with pytest.raises(AbortoPruebas):
        cfg_e2e.construir_configuracion_e2e(DESARROLLO)


def test_proteccion_solo_los_dos_nombres(monkeypatch):
    """RA-02.41: el nombre activo solo puede ser uno de los dos fijos; ninguna variable de entorno lo cambia."""
    assert proteccion.nombre_activo() == NOMBRE_PRUEBAS  # por omisión pytest no cambia

    # Ninguna variable de entorno elige el nombre.
    for variable in ("SQL_SERVER_DATABASE", "QDRANT_COLLECTION_NAME", "NOMBRE_PRUEBAS", "NOMBRE_PRUEBAS_ACTIVO"):
        monkeypatch.setenv(variable, NOMBRE_PRUEBAS_E2E)
    assert proteccion.nombre_activo() == NOMBRE_PRUEBAS
    with pytest.raises(AbortoPruebas):
        exigir_nombre_pruebas(NOMBRE_PRUEBAS_E2E, "la base de datos")

    # Cualquier otro nombre se rechaza y el activo no cambia.
    for invalido in ("db_ServIA", "justicia_docs", "SERVIA_PRUEBAS_E2E", "servia_pruebas_e2e2", "mi_servia_pruebas_e2e",
                     " servia_pruebas_e2e", "servia_pruebas_e2e\n", "", "master", "servia_pruebas; DROP DATABASE x;--",
                     None, 0, b"servia_pruebas"):
        with pytest.raises(AbortoPruebas):
            proteccion.fijar_nombre_activo(invalido)
        assert proteccion.nombre_activo() == NOMBRE_PRUEBAS

    try:
        proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS_E2E)
        assert proteccion.nombre_activo() == NOMBRE_PRUEBAS_E2E
        exigir_nombre_pruebas(NOMBRE_PRUEBAS_E2E, "la base de datos")
        with pytest.raises(AbortoPruebas) as error:  # con el nombre e2e activo, el de pytest ya no sirve
            exigir_nombre_pruebas(NOMBRE_PRUEBAS, "la base de datos")
        assert NOMBRE_PRUEBAS_E2E in str(error.value)

        # El DDL también valida contra el nombre activo, antes de abrir una conexión.
        llamadas = []
        for operacion in (lambda c: proteccion.crear_base(NOMBRE_PRUEBAS, c), lambda c: proteccion.eliminar_base("db_ServIA", c),
                          lambda c: proteccion.crear_coleccion(NOMBRE_PRUEBAS, c, 1024),
                          lambda c: proteccion.eliminar_coleccion("justicia_docs", c)):
            with pytest.raises(AbortoPruebas):
                operacion(lambda: llamadas.append("conectó"))
        assert llamadas == []
    finally:
        proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS)
    assert proteccion.nombre_activo() == NOMBRE_PRUEBAS


def test_carpeta_temporal_fuera_de_app(tmp_path, monkeypatch):
    """RA-02.41: la carpeta temporal de la instancia está fuera de `/app`; escribir ahí reiniciaría el servidor de desarrollo."""
    carpeta = cfg_e2e.CARPETA_E2E
    assert carpeta.is_absolute()
    assert carpeta.name == "servia_e2e"
    assert RAIZ_BACKEND not in carpeta.parents and carpeta != RAIZ_BACKEND
    assert carpeta.parent == Path(__import__("tempfile").gettempdir())

    # Dentro de la raíz del backend no se prepara.
    with pytest.raises(AbortoPruebas):
        cfg_e2e.preparar_carpeta(RAIZ_BACKEND / "servia_e2e")
    assert not (RAIZ_BACKEND / "servia_e2e").exists()

    # Fuera de ella, se crea limpia (reemplaza lo que dejó una corrida cortada) y queda como la de la sesión.
    monkeypatch.setitem(simulados._estado, "carpeta", None)
    destino = tmp_path / "servia_e2e"
    destino.mkdir()
    (destino / "resto_viejo").write_text("de una corrida cortada")
    cfg_e2e.preparar_carpeta(destino)
    assert destino.is_dir() and not (destino / "resto_viejo").exists()
    assert (destino.stat().st_mode & 0o077) == 0  # solo el dueño
    assert simulados.carpeta_temporal_de_la_sesion() == destino


# --- RA-02.49: el control no existe en el backend de desarrollo ---------------------------------------------

def test_control_ausente_en_main():
    """RA-02.49: `main.py` y el código de producción no incluyen el control; el router vive solo en la instancia."""
    fuentes = [RAIZ_BACKEND / "main.py", *sorted((RAIZ_BACKEND / "app").rglob("*.py"))]
    assert len(fuentes) > 10
    nombrados = [
        fuente.relative_to(RAIZ_BACKEND).as_posix() for fuente in fuentes
        if any(marca in fuente.read_text(encoding="utf-8") for marca in ("instancia_e2e", "pruebas-e2e"))
    ]
    assert nombrados == []

    rutas = {(metodo, ruta.path) for ruta in control.router.routes for metodo in ruta.methods}
    assert ("GET", "/pruebas-e2e/estado") in rutas
    assert ("POST", "/pruebas-e2e/apagar") in rutas
    assert all(ruta.startswith("/pruebas-e2e/") for _, ruta in rutas)


def test_el_control_pide_token_salvo_estado():
    """RA-02.49: `apagar` exige la cabecera con el token; `estado` es de solo lectura y no la pide."""
    contexto = control.Contexto(token="token-de-la-prueba", apagar=lambda: None, vigilante=Vigilante(60))
    control.exigir_token(contexto, "token-de-la-prueba")
    for malo in (None, "", "otro", "token-de-la-prueba "):
        with pytest.raises(control.HTTPException) as error:
            control.exigir_token(contexto, malo)
        assert error.value.status_code == 403


# --- RA-02.49: vigilante de inactividad --------------------------------------------------------------------------

class RelojFalso:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora


def test_vigilante_apaga_por_inactividad():
    """RA-02.49: sin peticiones al control durante 15 min el proceso se apaga solo; cada petición reinicia la cuenta."""
    assert LIMITE_INACTIVIDAD_SEGUNDOS == 15 * 60
    reloj = RelojFalso()
    vigilante = Vigilante(LIMITE_INACTIVIDAD_SEGUNDOS, reloj=reloj)
    apagados = []

    reloj.ahora += LIMITE_INACTIVIDAD_SEGUNDOS - 1
    assert vigilante.revisar(lambda: apagados.append(1)) is False and apagados == []

    vigilante.tocar()  # una petición al control reinicia la cuenta
    reloj.ahora += LIMITE_INACTIVIDAD_SEGUNDOS - 1
    assert vigilante.revisar(lambda: apagados.append(1)) is False and apagados == []

    reloj.ahora += 1
    assert vigilante.revisar(lambda: apagados.append(1)) is True and apagados == [1]
    assert vigilante.revisar(lambda: apagados.append(1)) is False and apagados == [1]  # no apaga dos veces


def test_vigilante_en_su_hilo_apaga_y_se_puede_detener():
    """RA-02.49: el hilo del vigilante llama a `apagar` al vencer el plazo; y se detiene sin apagar si se le pide."""
    apagado = threading.Event()
    vigilante = Vigilante(0.05)
    hilo = vigilante.iniciar(apagado.set, intervalo=0.01)
    assert apagado.wait(10), "el vigilante no apagó la instancia"
    hilo.join(10)
    assert not hilo.is_alive()

    no_debe_apagar = threading.Event()
    otro = Vigilante(3600)
    hilo = otro.iniciar(no_debe_apagar.set, intervalo=0.01)
    otro.detener()
    hilo.join(10)
    assert not hilo.is_alive() and not no_debe_apagar.is_set()


# --- Lanzador: --apagar -----------------------------------------------------------------------------------------

def test_apagar_sin_instancia_no_hace_nada(tmp_path):
    """RA-02.49: `--apagar` sin instancia en marcha (sin archivo de PID, o con un PID que ya no existe) termina sin error."""
    assert lanzador.apagar_instancia(tmp_path / "no_existe", espera=0.1) is False

    carpeta = tmp_path / "servia_e2e"
    carpeta.mkdir()
    (carpeta / "pid").write_text("2147483646")  # un PID que no existe
    assert lanzador.apagar_instancia(carpeta, espera=0.1) is False


# --- RA-02.43: el registro de la instancia no guarda contraseñas ---------------------------------------------------

def test_registro_cuenta_contrasenas_recibidas(tmp_path):
    """RA-02.43: la instancia recuerda en memoria las contraseñas recibidas y, al apagarse, devuelve solo cuántas
    aparecen en su registro (nunca cuáles); las vacías no cuentan."""
    registro = RegistroContrasenas()
    registro.recordar("PRUEBAclaveUno")
    registro.recordar("PRUEBAclaveDos")
    registro.recordar("")
    assert registro.contar_en("sin nada sensible\nGET /pruebas-e2e/estado") == 0
    assert registro.contar_en("a PRUEBAclaveUno b\nPRUEBAclaveUno y PRUEBAclaveDos") == 3

    bitacora = tmp_path / "instancia.log"
    bitacora.write_text("INFO: login con PRUEBAclaveDos\n")
    apagados = []
    contexto = control.Contexto(token="t", apagar=lambda: apagados.append(1), vigilante=Vigilante(60),
                                contrasenas=registro, registro=bitacora)
    respuesta = control.apagar(contexto)
    assert apagados == [1]
    assert respuesta == {"apagando": True, "coincidencias_en_registro": 1}

    sin_registro = control.Contexto(token="t", apagar=lambda: None, vigilante=Vigilante(60),
                                    contrasenas=registro, registro=tmp_path / "no_existe.log")
    assert control.apagar(sin_registro)["coincidencias_en_registro"] == 0


def test_el_control_de_usuarios_recuerda_la_contrasena_y_no_la_devuelve(monkeypatch):
    """RA-02.43 / RA-02.42: `POST /usuarios` guarda la contraseña recibida solo en el registro en memoria, la pasa a quien crea
    el usuario y responde sin ella; un rol que no existe se rechaza con 400 y no recuerda nada."""
    creados = []

    def crear_falso(rol, contrasena, temporal, inactivo):
        creados.append((rol, contrasena, temporal, inactivo))
        return SimpleNamespace(cedula="PRUEBA000001", nombre_usuario="PRUEBA_admin_1", correo="prueba1.admin@prueba.invalid",
                               contrasena="no-debe-salir", rol="Administrador")

    monkeypatch.setattr(control, "crear_usuario_e2e", crear_falso)
    contexto = control.Contexto(token="t", apagar=lambda: None, vigilante=Vigilante(60))
    cuerpo = control.CuerpoUsuario(rol="administrador", contrasena="PRUEBAclaveSecreta", temporal=True, inactivo=False)
    respuesta = control.usuarios(cuerpo, contexto)

    assert creados == [("administrador", "PRUEBAclaveSecreta", True, False)]
    assert respuesta == {"cedula": "PRUEBA000001", "nombre_usuario": "PRUEBA_admin_1", "correo": "prueba1.admin@prueba.invalid",
                         "rol": "Administrador", "temporal": True, "inactivo": False}
    assert "PRUEBAclaveSecreta" not in repr(respuesta) and "no-debe-salir" not in repr(respuesta)
    assert contexto.contrasenas.contar_en("x PRUEBAclaveSecreta y") == 1

    with pytest.raises(control.HTTPException) as error:
        control.usuarios(control.CuerpoUsuario(rol="superusuario", contrasena="PRUEBAotra"), contexto)
    assert error.value.status_code == 400
    assert contexto.contrasenas.contar_en("PRUEBAotra") == 0 and len(creados) == 1


# --- RA-02.42: limpieza total y residuos ---------------------------------------------------------------------------------

class SqlFalso:
    """Registra lo que se borra y responde conteos por tabla; no abre ninguna conexión."""

    def __init__(self, conteos=None):
        self.sentencias = []
        self.conteos = dict(conteos or {})

    def borrar(self, sentencia, parametros):
        self.sentencias.append((sentencia, dict(parametros)))
        return 0

    def contar(self, sentencia, parametros):
        tabla = sentencia.split("FROM ")[1].split()[0]
        return self.conteos.get(tabla, 0)


class QdrantFalso:
    def __init__(self, ids=()):
        self.ids = list(ids)
        self.borrados = []

    def scroll(self, collection_name, limit, offset, with_payload, with_vectors):
        return [SimpleNamespace(id=i) for i in self.ids], None

    def delete(self, collection_name, points_selector, wait):
        self.borrados.append(list(points_selector.points))
        self.ids = []

    def count(self, collection_name, exact):
        return SimpleNamespace(count=len(self.ids))


def _destino_e2e(tmp_path, **cambios):
    raiz = tmp_path / "servia_e2e"
    archivos = raiz / "tmp1" / "uploads"
    avatares = raiz / "tmp1" / "avatares"
    archivos.mkdir(parents=True, exist_ok=True)
    avatares.mkdir(parents=True, exist_ok=True)
    valores = dict(base=NOMBRE_PRUEBAS_E2E, coleccion=NOMBRE_PRUEBAS_E2E, carpetas=[archivos, avatares], raiz_carpetas=raiz,
                   usuarios_sembrados=("000000000",))
    valores.update(cambios)
    return simulados_e2e.DestinoE2E(**valores)


def test_limpieza_rechaza_otra_base(nombre_e2e, tmp_path):
    """RA-02.42: la limpieza total se niega, antes de borrar nada, con una base, una colección o una carpeta que no sean las
    de la instancia (desarrollo, la de pytest o cualquier otra), y con el nombre activo de pytest; el conteo también."""
    afuera = tmp_path / "uploads"
    afuera.mkdir()
    (afuera / "PRUEBA_dato.txt").write_text("x")
    for base in ("db_ServIA", NOMBRE_PRUEBAS, "justicia_docs", "servia_pruebas_e2e ", None):
        sql, qdrant = SqlFalso(), QdrantFalso(["a"])
        destino = _destino_e2e(tmp_path, base=base, borrar=sql.borrar, contar=sql.contar, qdrant=qdrant)
        with pytest.raises(AbortoPruebas):
            simulados_e2e.limpiar_todo(destino)
        with pytest.raises(AbortoPruebas):
            simulados_e2e.contar_residuos_e2e(destino)
        assert sql.sentencias == [] and qdrant.borrados == []
    for coleccion in ("justicia_docs", NOMBRE_PRUEBAS):
        sql, qdrant = SqlFalso(), QdrantFalso(["a"])
        destino = _destino_e2e(tmp_path, coleccion=coleccion, borrar=sql.borrar, contar=sql.contar, qdrant=qdrant)
        with pytest.raises(AbortoPruebas):
            simulados_e2e.limpiar_todo(destino)
        assert sql.sentencias == [] and qdrant.borrados == []
    for carpeta in (afuera, tmp_path, tmp_path / "servia_e2e"):
        destino = _destino_e2e(tmp_path, carpetas=[carpeta])
        with pytest.raises(AbortoPruebas):
            simulados_e2e.limpiar_todo(destino)
        assert (afuera / "PRUEBA_dato.txt").exists()
    otra_raiz = tmp_path / "otra"
    otra_raiz.mkdir()
    with pytest.raises(AbortoPruebas):
        simulados_e2e.limpiar_todo(_destino_e2e(tmp_path, carpetas=[otra_raiz / "x"], raiz_carpetas=otra_raiz))

    # Con el nombre activo de pytest (sin la fixture) tampoco: la limpieza total es solo de la instancia e2e.
    proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS)
    sql = SqlFalso()
    with pytest.raises(AbortoPruebas):
        simulados_e2e.limpiar_todo(_destino_e2e(tmp_path, base=NOMBRE_PRUEBAS, coleccion=NOMBRE_PRUEBAS,
                                                borrar=sql.borrar, contar=sql.contar))
    assert sql.sentencias == []


def test_limpieza_total_borra_todo_menos_catalogos_y_administrador(nombre_e2e, tmp_path):
    """RA-02.42: borra en orden de claves foráneas todas las filas de las seis tablas (de usuarios, salvo los sembrados), los
    puntos, los archivos, Redis, las conversaciones y el buzón; nunca toca los catálogos; y el conteo lo confirma."""
    sql = SqlFalso({"T_Usuario": 3, "T_Bitacora": 2})
    qdrant = QdrantFalso(["p1", "p2"])
    llamadas = []
    destino = _destino_e2e(
        tmp_path, borrar=sql.borrar, contar=sql.contar, qdrant=qdrant,
        limpiar_redis=lambda: llamadas.append("redis"), claves_redis=lambda: 1,
        limpiar_conversaciones=lambda: llamadas.append("conversaciones"), conversaciones=lambda: 2,
        vaciar_buzon=lambda: llamadas.append("buzon"), mensajes_buzon=lambda: 4,
    )
    carpeta_uploads, carpeta_avatares = destino.carpetas
    (carpeta_uploads / "PRUEBA-1").mkdir()
    (carpeta_uploads / "PRUEBA-1" / "a.txt").write_text("x")
    (carpeta_avatares / "b.png").write_text("x")

    residuos = simulados_e2e.contar_residuos_e2e(destino)
    assert residuos["filas"]["T_Usuario"] == 3 and residuos["filas"]["T_Bitacora"] == 2
    assert residuos["puntos"] == 2 and residuos["archivos"] == 2 and residuos["claves_redis"] == 1
    assert residuos["conversaciones"] == 2 and residuos["buzon"] == 4
    assert residuos["total"] == 5 + 2 + 2 + 1 + 2 + 4 and "T_Usuario: 3" in residuos["texto"]

    simulados_e2e.limpiar_todo(destino)

    tablas = [sentencia.split("FROM ")[1].split()[0] for sentencia, _ in sql.sentencias]
    assert tablas == ["T_Bitacora", "T_Notebook", "T_Expediente_Documento", "T_Documento", "T_Expediente", "T_Usuario"]
    sentencia_usuarios, parametros = sql.sentencias[-1]
    assert "NOT IN" in sentencia_usuarios and list(parametros.values()) == ["000000000"]
    assert all("WHERE" not in sentencia for sentencia, _ in sql.sentencias[:-1])
    assert qdrant.borrados == [["p1", "p2"]]
    assert sorted(llamadas) == ["buzon", "conversaciones", "redis"]
    assert list(carpeta_uploads.iterdir()) == [] and list(carpeta_avatares.iterdir()) == []
    assert carpeta_uploads.is_dir() and carpeta_avatares.is_dir()

    limpio = simulados_e2e.contar_residuos_e2e(_destino_e2e(tmp_path, borrar=sql.borrar, contar=SqlFalso().contar,
                                                           qdrant=qdrant))
    assert limpio["total"] == 0 and limpio["texto"] == "ninguno"


def test_limpieza_reintenta_un_error_transitorio_de_la_base(nombre_e2e, tmp_path):
    """RA-02.42 / RA-02.47: una petición del navegador que sigue en vuelo puede chocar con el borrado (interbloqueo, clave
    foránea de una fila recién escrita). La limpieza repite el borrado de las tablas dentro de un plazo acotado y termina bien;
    si el error persiste, aborta y nombra la tabla y el error."""
    class SqlInestable(SqlFalso):
        def __init__(self, fallos):
            super().__init__()
            self.fallos = fallos

        def borrar(self, sentencia, parametros):
            if self.fallos > 0 and "T_Usuario" in sentencia:
                self.fallos -= 1
                raise RuntimeError("Transaction (Process ID 55) was deadlocked on lock resources (1205)")
            return super().borrar(sentencia, parametros)

    sql = SqlInestable(fallos=2)
    destino = _destino_e2e(tmp_path, borrar=sql.borrar, contar=sql.contar, pausa_reintento=0.0)
    simulados_e2e.limpiar_todo(destino)
    tablas = [sentencia.split("FROM ")[1].split()[0] for sentencia, _ in sql.sentencias]
    assert tablas[-1] == "T_Usuario" and tablas.count("T_Usuario") == 1  # los dos primeros intentos fallaron antes de registrarse
    assert tablas.count("T_Bitacora") == 3  # cada intento repite toda la secuencia, en el orden de las claves foráneas

    sql = SqlInestable(fallos=10**6)
    destino = _destino_e2e(tmp_path, borrar=sql.borrar, contar=sql.contar, plazo_reintento=0.0, pausa_reintento=0.0)
    with pytest.raises(AbortoPruebas) as error:
        simulados_e2e.limpiar_todo(destino)
    assert "T_Usuario" in str(error.value) and "1205" in str(error.value)


def test_limpieza_incluye_usuarios_sin_prefijo_prueba(nombre_e2e, tmp_path):
    """RA-02.42: la cuenta creada por el formulario (cédula numérica, sin `PRUEBA`) se cuenta y se borra como cualquier
    usuario no sembrado: el filtro solo excluye a los sembrados y no depende de ningún prefijo en la cédula."""
    sql = SqlFalso({"T_Usuario": 1})
    destino = _destino_e2e(tmp_path, borrar=sql.borrar, contar=sql.contar)
    assert simulados_e2e.contar_residuos_e2e(destino)["filas"]["T_Usuario"] == 1
    simulados_e2e.limpiar_todo(destino)
    sentencia, parametros = sql.sentencias[-1]
    assert sentencia.startswith("DELETE FROM T_Usuario") and "NOT IN" in sentencia
    assert "LIKE" not in sentencia.upper() and "PRUEBA" not in sentencia
    assert list(parametros.values()) == ["000000000"]


# --- RA-02.49 (T5): recuperación y bitácora ---------------------------------------------------------------------------------

def _correo_con_codigos(*envios):
    """Un correo simulado que ya «envió» los correos dados `(destinatario, texto)`."""
    import asyncio
    from email.message import EmailMessage

    correo = simulados.CorreoSimulado()

    async def enviar():
        for destinatario, texto in envios:
            mensaje = EmailMessage()
            mensaje["To"] = destinatario
            mensaje["Subject"] = "PRUEBA recuperación"
            mensaje.set_content(texto)
            await correo.enviar(mensaje)

    asyncio.run(enviar())
    return correo


class AlmacenFalso:
    """Lo que el control usa del Redis controlable, sin abrir nada."""

    def __init__(self):
        self._fallo = None
        self.avanzado = []

    def no_responde(self, tipo="conexion"):
        self._fallo = tipo

    def responder_bien(self):
        self._fallo = None

    def avanzar(self, segundos):
        self.avanzado.append(segundos)


def _contexto_con_capacidades(correo=None, almacen=None):
    return control.Contexto(token="t", apagar=lambda: None, vigilante=Vigilante(60),
                            correo=correo or simulados.CorreoSimulado(), almacen=almacen or AlmacenFalso())


def test_codigo_del_correo_es_el_ultimo_del_destinatario_y_no_se_muestra():
    """RF-03.41 / RA-02.49: el control lee el código de 6 dígitos del ÚLTIMO correo al destinatario; sin correo o sin código,
    falla sin repetir el contenido."""
    correo = _correo_con_codigos(
        ("ana@prueba.invalid", "Tu código de verificación es: 111111"),
        ("beto@prueba.invalid", "Tu código de verificación es: 222222"),
        ("Ana <ANA@prueba.invalid>", "Hola. Tu código de verificación es: 333333 Vence en 15 minutos."),
        ("ana@prueba.invalid", "Un aviso sin código"),
    )
    assert simulados_e2e.codigo_del_correo(correo, "ana@prueba.invalid") == "333333"
    assert simulados_e2e.codigo_del_correo(correo, "beto@prueba.invalid") == "222222"
    for destinatario in ("nadie@prueba.invalid", ""):
        with pytest.raises(LookupError) as error:
            simulados_e2e.codigo_del_correo(correo, destinatario)
        assert "333333" not in str(error.value) and "222222" not in str(error.value)


def test_el_control_lee_el_codigo_y_responde_404_si_no_hay():
    """RA-02.49: `GET /correo/codigo` devuelve solo el código; un destinatario sin correo con código da 404 sin contenido."""
    contexto = _contexto_con_capacidades(_correo_con_codigos(("ana@prueba.invalid", "Tu código de verificación es: 444444")))
    assert control.leer_codigo("ana@prueba.invalid", contexto) == {"codigo": "444444"}
    with pytest.raises(control.HTTPException) as error:
        control.leer_codigo("otra@prueba.invalid", contexto)
    assert error.value.status_code == 404 and "444444" not in str(error.value.detail)


def test_el_control_programa_correo_almacen_y_reloj():
    """RA-02.49: programar el fallo del correo y del almacén y avanzar el reloj; `capacidades` lo refleja; valores inválidos, 400."""
    contexto = _contexto_con_capacidades()
    assert control.capacidades(contexto) == {"correo_en_fallo": False, "almacen_no_disponible": False, "correos_enviados": 0}

    control.programar_correo(control.CuerpoCorreo(falla=True), contexto)
    control.programar_almacen(control.CuerpoAlmacen(disponible=False, tipo="tiempo"), contexto)
    assert control.capacidades(contexto)["correo_en_fallo"] is True
    assert control.capacidades(contexto)["almacen_no_disponible"] is True
    assert contexto.almacen._fallo == "tiempo"
    control.programar_correo(control.CuerpoCorreo(falla=False), contexto)
    control.programar_almacen(control.CuerpoAlmacen(disponible=True), contexto)
    assert control.capacidades(contexto) == {"correo_en_fallo": False, "almacen_no_disponible": False, "correos_enviados": 0}

    assert control.avanzar_reloj(control.CuerpoReloj(segundos=901), contexto) == {"avanzado": 901}
    assert contexto.almacen.avanzado == [901]
    for malo in (0, -5, 86401):
        with pytest.raises(control.HTTPException) as error:
            control.avanzar_reloj(control.CuerpoReloj(segundos=malo), contexto)
        assert error.value.status_code == 400
    with pytest.raises(control.HTTPException) as error:
        control.programar_almacen(control.CuerpoAlmacen(disponible=False, tipo="otro"), contexto)
    assert error.value.status_code == 400
    assert contexto.almacen.avanzado == [901]


def test_el_control_de_bitacora_valida_el_tipo_y_registra(monkeypatch):
    """RF-22.40 / RF-21.41: `POST /bitacora` acepta solo los tipos del catálogo del control y pasa cédula y tema a quien escribe
    la fila; un tipo desconocido o una cédula vacía, 400."""
    escritas = []
    monkeypatch.setattr(simulados_e2e, "registrar_fila_de_bitacora",
                        lambda tipo, cedula, tema: escritas.append((tipo, cedula, tema)) or 77)
    contexto = _contexto_con_capacidades()
    assert control.crear_fila_de_bitacora(
        control.CuerpoBitacora(cedula="PRUEBA000001", tipo="carga_cancelada", tema="99-000001-0001-PE"), contexto
    ) == {"id": 77, "tipo": "carga_cancelada"}
    assert escritas == [("carga_cancelada", "PRUEBA000001", "99-000001-0001-PE")]
    for malo in (control.CuerpoBitacora(cedula="PRUEBA000001", tipo="inventado"),
                 control.CuerpoBitacora(cedula=" ", tipo="carga_cancelada")):
        with pytest.raises(control.HTTPException) as error:
            control.crear_fila_de_bitacora(malo, contexto)
        assert error.value.status_code == 400
    assert len(escritas) == 1
    assert {"carga_iniciada", "carga_rechazada", "carga_cancelada", "carga_error", "crear_notebook",
            "quitar_documento_notebook", "gestionar_conversacion"} <= set(simulados_e2e.TIPOS_DE_BITACORA)


def test_los_endpoints_nuevos_estan_en_el_router_y_piden_token():
    """RA-02.49: las rutas de la T5 viven solo en el router del control y todas dependen del token."""
    rutas = {(metodo, ruta.path): ruta for ruta in control.router.routes for metodo in ruta.methods}
    for clave in (("GET", "/pruebas-e2e/correo/codigo"), ("POST", "/pruebas-e2e/correo"), ("POST", "/pruebas-e2e/almacen"),
                  ("POST", "/pruebas-e2e/reloj"), ("POST", "/pruebas-e2e/bitacora"), ("GET", "/pruebas-e2e/capacidades")):
        assert clave in rutas, clave
        dependencias = [d.call for d in rutas[clave].dependant.dependencies]
        assert control._con_token in dependencias, clave


def test_la_limpieza_restablece_el_almacen_y_la_falla_se_nombra(nombre_e2e, tmp_path):
    """RA-02.42 / RA-02.49: la limpieza total devuelve el almacén temporal a la normalidad; si ese paso falla, el error lo nombra
    y los demás pasos igual se ejecutan."""
    llamadas = []
    destino = _destino_e2e(tmp_path, restablecer_almacen=lambda: llamadas.append("almacen"),
                           limpiar_redis=lambda: llamadas.append("redis"))
    simulados_e2e.limpiar_todo(destino)
    assert llamadas == ["almacen", "redis"]

    def romper():
        raise RuntimeError("sin almacén")

    llamadas.clear()
    destino = _destino_e2e(tmp_path, restablecer_almacen=romper, limpiar_redis=lambda: llamadas.append("redis"))
    with pytest.raises(AbortoPruebas) as error:
        simulados_e2e.limpiar_todo(destino)
    assert "almacén temporal" in str(error.value) and llamadas == ["redis"]



# --- RA-02.49 (T6): motor programable --------------------------------------------------------------------------------------

CONTEXTO_CON_DOS_ARCHIVOS = (
    "Eres JusticBot, un asistente legal.\n"
    "**DOCUMENTO 1**\nArchivo: PRUEBA_uno.txt\nExpediente: 99-000001-0001-PE\nMostrando chunks: 1-1 de 1 totales\n"
    "**DOCUMENTO 2**\nArchivo: PRUEBA_dos.pdf\nExpediente: NB-7\nMostrando chunks: 1-1 de 1 totales\n"
    "**DOCUMENTO 3**\nArchivo: PRUEBA_uno.txt\nExpediente: 99-000001-0001-PE\n"
)
CONTEXTO_DE_REFORMULACION = "Eres JusticBot, experto en reformular preguntas legales para búsqueda vectorial."


def _mensajes(sistema, pregunta="¿Qué dice el documento?"):
    from langchain_core.messages import HumanMessage, SystemMessage

    return [SystemMessage(content=sistema), HumanMessage(content=pregunta)]


def _hasta(condicion, plazo=5.0):
    """Espera a que `condicion()` sea cierta, mirando cada 10 ms, y falla si no ocurre en `plazo` segundos."""
    limite = time.monotonic() + plazo
    while not condicion():
        assert time.monotonic() < limite, "la condición no se cumplió a tiempo"
        threading.Event().wait(0.01)


def _en_un_hilo(accion):
    """Ejecuta `accion()` en un hilo; devuelve `(hilo, resultado)` con `resultado['valor']` o `resultado['error']`."""
    resultado = {}

    def correr():
        try:
            resultado["valor"] = accion()
        except BaseException as error:  # la prueba decide qué hacer con él
            resultado["error"] = error

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    return hilo, resultado


def test_motor_programable(tmp_path):
    """RA-02.49 (RF-11.40, 11.41, 11.42, 11.43, 16.40): el motor simulado cita los archivos del contexto, sigue una secuencia,
    falla por conexión, se retiene tras N fragmentos o sin emitir nada, y se restablece; el control valida lo que recibe y la
    limpieza total lo restablece ANTES de borrar."""
    estado = simulados_e2e.EstadoMotor(plazo=10)
    motor = simulados_e2e.clase_motor_programable()(estado=estado)
    assert isinstance(motor, simulados._Simulado)  # `comprobar_simulados` lo sigue reconociendo

    # 1. Por omisión cita, una sola vez cada archivo, con la ruta que la interfaz vuelve descargable (tema o clave de notebook).
    respuesta = motor.invoke(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS)).content
    assert respuesta.count("(uploads/99-000001-0001-PE/PRUEBA_uno.txt)") == 1
    assert respuesta.count("(uploads/NB-7/PRUEBA_dos.pdf)") == 1
    sin_contexto = motor.invoke(_mensajes("Eres JusticBot, un asistente legal.")).content
    assert "uploads/" not in sin_contexto and "No encontré" in sin_contexto
    # El encabezado con el que el chat arma el contexto de verdad (con o sin ruta) se reconoce igual.
    formateado = (
        "EXPEDIENTE: 99-000009-0001-PE (1 documentos)\n"
        "**Expediente:** 99-000009-0001-PE | **Archivo:** PRUEBA_tres.txt | **Pág:** 1-3\n"
        "**Ruta:** /app/uploads/99-000009-0001-PE/PRUEBA_tres.txt\n---\ntexto\n---\n"
        "**Expediente:** NB-8 | **Archivo:** PRUEBA_cuatro.png\n---\ntexto\n---\n"
    )
    assert simulados_e2e.documentos_del_contexto(formateado) == [
        "uploads/99-000009-0001-PE/PRUEBA_tres.txt", "uploads/NB-8/PRUEBA_cuatro.png"]
    # El streaming entrega el mismo texto, en fragmentos.
    fragmentos = [pieza.content for pieza in motor.stream(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS))]
    assert len(fragmentos) > 1 and "".join(fragmentos) == respuesta

    # 2. La reformulación de la pregunta con historial no cuenta como respuesta ni consume la secuencia.
    estado.configurar(secuencia=["", "Segunda"])
    antes = estado.estado()["consultas"]
    assert motor.invoke(_mensajes(CONTEXTO_DE_REFORMULACION, "pregunta original")).content == "pregunta original"
    assert estado.estado()["consultas"] == antes and estado.estado()["secuencia_pendiente"] == 2

    # 3. Secuencia: vacío, respuesta y, agotada, el modo de siempre.
    assert [pieza.content for pieza in motor.stream(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS))] == [""]
    assert motor.invoke(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS)).content == "Segunda"
    assert estado.estado()["secuencia_pendiente"] == 0
    assert "PRUEBA_uno.txt" in motor.invoke(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS)).content

    # 4. Texto fijo y fallo por conexión (en el modo y como paso de la secuencia).
    estado.configurar(modo="texto", texto="Respuesta fija de PRUEBA.")
    assert motor.invoke(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS)).content == "Respuesta fija de PRUEBA."
    for programa in ({"modo": "conexion"}, {"secuencia": [None]}):
        estado.configurar(**programa)
        with pytest.raises(ConnectionError) as error:
            motor.invoke(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS))
        assert simulados_e2e.TEXTO_DE_FALLO_DE_CONEXION in str(error.value)
        estado.configurar(**programa)
        with pytest.raises(ConnectionError):
            list(motor.stream(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS)))

    # 5. Retenida tras N fragmentos: llegan N y espera; al liberar llegan los demás.
    estado.configurar(modo="texto", texto="uno dos tres cuatro", retener_tras=2)
    recibidos = []
    hilo, resultado = _en_un_hilo(lambda: [recibidos.append(p.content) for p in motor.stream(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS))])
    _hasta(lambda: estado.compuerta.esperando == 1)
    assert recibidos == ["uno ", "dos "] and hilo.is_alive()
    assert estado.estado()["retenida"] is True and estado.estado()["esperando"] == 1
    estado.liberar()
    hilo.join(5)
    assert not hilo.is_alive() and "error" not in resultado
    assert "".join(recibidos) == "uno dos tres cuatro" and estado.estado()["retenida"] is False

    # 6. Sin datos: no llega nada mientras está retenido; al liberar termina vacío (la interfaz ya se rindió).
    estado.configurar(modo="sin_datos")
    recibidos.clear()
    hilo, resultado = _en_un_hilo(lambda: [recibidos.append(p.content) for p in motor.stream(_mensajes(CONTEXTO_CON_DOS_ARCHIVOS))])
    _hasta(lambda: estado.compuerta.esperando == 1)
    assert recibidos == []
    estado.liberar()
    hilo.join(5)
    assert not hilo.is_alive() and "error" not in resultado and recibidos == [""]

    # 7. El plazo corta una retención olvidada: no deja colgado el servidor.
    corto = simulados_e2e.EstadoMotor(plazo=0.05)
    corto.configurar(modo="texto", texto="a b", retener_tras=0)
    assert simulados_e2e.clase_motor_programable()(estado=corto).invoke(_mensajes("x")).content == "a b"

    # 8. Restablecer: modo de cita, sin secuencia, sin retención y sin contar.
    estado.configurar(modo="texto", texto="x", secuencia=["y"], retener_tras=1)
    estado.restablecer()
    assert estado.estado() == {"modo": "cita", "secuencia_pendiente": 0, "retener_tras": None, "retenida": False,
                               "esperando": 0, "consultas": 0}

    # 9. Lo inválido se rechaza sin cambiar nada.
    for malo in ({"modo": "otro"}, {"modo": "texto"}, {"retener_tras": -1}, {"secuencia": ["a"] * 21},
                 {"modo": "texto", "texto": "x" * 5001}):
        with pytest.raises(ValueError):
            estado.configurar(**malo)
    assert estado.estado()["modo"] == "cita"

    # 10. Las rutas del control: validan (400), piden el control montado (503) y devuelven el estado.
    controles = simulados_e2e.Controles(motor=estado, ingesta=None, notebooks=None)
    contexto = control.Contexto(token="t", apagar=lambda: None, vigilante=Vigilante(60), controles=controles)
    assert control.programar_motor(control.CuerpoMotor(modo="texto", texto="t", retener_tras=0), contexto)["retenida"] is True
    assert control.leer_motor(contexto)["modo"] == "texto"
    assert control.liberar_motor(contexto)["retenida"] is False
    with pytest.raises(control.HTTPException) as error:
        control.programar_motor(control.CuerpoMotor(modo="otro"), contexto)
    assert error.value.status_code == 400
    with pytest.raises(control.HTTPException) as error:
        control.leer_motor(control.Contexto(token="t", apagar=lambda: None, vigilante=Vigilante(60)))
    assert error.value.status_code == 503
    rutas = {(metodo, ruta.path) for ruta in control.router.routes for metodo in ruta.methods}
    assert {("GET", "/pruebas-e2e/motor"), ("POST", "/pruebas-e2e/motor"), ("POST", "/pruebas-e2e/motor/liberar")} <= rutas

    # 11. La limpieza total restablece los controles ANTES de borrar nada.
    orden = []
    sql = SqlFalso()
    sql.borrar = lambda sentencia, parametros: orden.append("borrar") or 0
    estado.configurar(modo="conexion")
    destino = _destino_e2e(tmp_path, borrar=sql.borrar,
                           restablecer_controles=lambda: (orden.append("controles"), estado.restablecer()))
    proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS_E2E)
    try:
        simulados_e2e.limpiar_todo(destino)
    finally:
        proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS)
    assert orden[0] == "controles" and orden.count("borrar") == 6 and estado.estado()["modo"] == "cita"
