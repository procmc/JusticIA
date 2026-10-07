"""Pruebas de T4 (spec 002, RA-02.3 y RA-02.4): la espera de servicios y el punto protegido de DDL.

Ninguna abre una conexión real: el servicio, el reloj y la conexión a SQL Server son simulados, y
el guardián de las unitarias frena cualquier intento de usar el servidor de verdad.
"""
import re
import socket

import pytest

from tests.soporte import entorno, proteccion
from tests.soporte.nombres import ESPERA_SERVICIOS_SEGUNDOS, NOMBRE_PRUEBAS
from tests.soporte.proteccion import AbortoPruebas

# Nombres que el punto de DDL debe rechazar sin conectarse (los mismos de la protección, RA-02.3).
NOMBRES_INVALIDOS = [
    pytest.param("db_ServIA", id="base-de-desarrollo"),
    pytest.param("SERVIA_PRUEBAS", id="mayusculas"),
    pytest.param("mi_servia_pruebas", id="lo-contiene"),
    pytest.param("servia_pruebas_2", id="lo-contiene-despues"),
    pytest.param("", id="vacio"),
    pytest.param("servia_pruebas]; DROP DATABASE db_ServIA; --", id="inyeccion"),
    pytest.param("master", id="master"),
    pytest.param(None, id="no-es-texto"),
]


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ninguna prueba de este archivo abre una conexión de red."""
    def _prohibido(*args, **kwargs):
        raise AssertionError("La prueba intentó abrir una conexión de red")

    monkeypatch.setattr(socket.socket, "connect", _prohibido)
    monkeypatch.setattr(socket, "create_connection", _prohibido)


class RelojSimulado:
    """Reloj y pausa de mentira: dormir solo adelanta la hora, así 60 s de espera no duran 60 s."""

    def __init__(self):
        self.ahora = 1000.0
        self.pausas = []

    def reloj(self) -> float:
        return self.ahora

    def pausa(self, segundos: float) -> None:
        self.pausas.append(segundos)
        self.ahora += segundos


class ConexionSimulada:
    """Ocupa el lugar de la conexión a `master`: registra el SQL que recibe y si se cerró."""

    def __init__(self, error=None):
        self.sentencias = []
        self.cerrada = False
        self._error = error

    def execute(self, sql, *args):
        self.sentencias.append(sql)
        if self._error is not None:
            raise self._error

    def close(self):
        self.cerrada = True


class FabricaDeConexiones:
    """`conectar()` de mentira: cuenta las veces que se llama y entrega la conexión simulada."""

    def __init__(self, conexion=None):
        self.llamadas = 0
        self.conexion = conexion or ConexionSimulada()

    def __call__(self):
        self.llamadas += 1
        return self.conexion


# --- esperar_servicio (RA-02.4) -----------------------------------------------------------------------

def test_esperar_servicio_sigue_intentando_hasta_que_responde_al_tercer_intento():
    """RA-02.4: un servicio que arranca tarde se espera: responde al tercer intento y la suite sigue."""
    tiempo = RelojSimulado()
    intentos = []

    def intentar():
        intentos.append(tiempo.reloj())
        if len(intentos) < 3:
            raise ConnectionError("todavía arrancando")

    entorno.esperar_servicio("SQL Server", intentar, reloj=tiempo.reloj, pausa=tiempo.pausa)

    assert len(intentos) == 3
    assert len(tiempo.pausas) == 2  # una pausa entre cada par de intentos, ninguna después del éxito


def test_esperar_servicio_responde_a_la_primera_sin_pausar():
    tiempo = RelojSimulado()
    entorno.esperar_servicio("Qdrant", lambda: None, reloj=tiempo.reloj, pausa=tiempo.pausa)
    assert tiempo.pausas == []


def test_esperar_servicio_que_nunca_responde_aborta_a_los_60_segundos_y_nombra_el_servicio():
    """RA-02.4: pasados 60 s (de reloj simulado) aborta con un mensaje en español que dice qué servicio no respondió."""
    tiempo = RelojSimulado()
    inicio = tiempo.reloj()
    intentos = []

    def intentar():
        intentos.append(1)
        raise ConnectionError("nunca responde")

    with pytest.raises(AbortoPruebas) as error:
        entorno.esperar_servicio("SQL Server", intentar, reloj=tiempo.reloj, pausa=tiempo.pausa)

    mensaje = str(error.value)
    assert "SQL Server" in mensaje
    assert "60" in mensaje
    assert "no respondi" in mensaje.lower()
    assert tiempo.reloj() - inicio >= ESPERA_SERVICIOS_SEGUNDOS
    assert len(intentos) > 3  # reintentó varias veces antes de rendirse


@pytest.mark.parametrize("servicio", ["SQL Server", "Qdrant", "Tika"])
def test_el_mensaje_de_espera_agotada_nombra_cada_servicio(servicio):
    tiempo = RelojSimulado()
    with pytest.raises(AbortoPruebas, match=servicio):
        entorno.esperar_servicio(servicio, lambda: (_ for _ in ()).throw(OSError("x")),
                                 reloj=tiempo.reloj, pausa=tiempo.pausa)


def test_el_mensaje_de_espera_agotada_no_muestra_el_texto_del_error_del_servicio():
    """Los errores de conexión pueden traer direcciones o usuarios: el mensaje solo dice el tipo de error."""
    tiempo = RelojSimulado()

    def intentar():
        raise RuntimeError("clave-secreta-del-servidor")

    with pytest.raises(AbortoPruebas) as error:
        entorno.esperar_servicio("SQL Server", intentar, reloj=tiempo.reloj, pausa=tiempo.pausa)
    assert "clave-secreta-del-servidor" not in str(error.value)
    assert "RuntimeError" in str(error.value)


def test_la_espera_por_omision_es_de_60_segundos():
    """RA-02.4: sin indicar otra cosa, `esperar_servicio` se rinde a los 60 segundos del reloj."""
    tiempo = RelojSimulado()
    assert ESPERA_SERVICIOS_SEGUNDOS == 60
    with pytest.raises(AbortoPruebas):
        entorno.esperar_servicio("Tika", lambda: 1 / 0, reloj=tiempo.reloj, pausa=tiempo.pausa)
    assert 60 <= tiempo.reloj() - 1000.0 < 70


# --- crear_base y eliminar_base: el único punto de DDL (RA-02.3, RA-02.4) ------------------------------

@pytest.mark.parametrize("funcion", [proteccion.crear_base, proteccion.eliminar_base],
                         ids=["crear_base", "eliminar_base"])
@pytest.mark.parametrize("nombre", NOMBRES_INVALIDOS)
def test_el_punto_de_ddl_se_niega_con_un_nombre_invalido_sin_conectarse(funcion, nombre):
    """RA-02.3: con cualquier nombre que no sea el de pruebas, aborta ANTES de abrir la conexión."""
    conectar = FabricaDeConexiones()
    with pytest.raises(AbortoPruebas):
        funcion(nombre, conectar)
    assert conectar.llamadas == 0
    assert conectar.conexion.sentencias == []


def test_crear_base_con_el_nombre_de_pruebas_crea_solo_esa_base():
    """RA-02.4: una sola sentencia, sobre la base de pruebas, y la conexión se cierra."""
    conectar = FabricaDeConexiones()
    proteccion.crear_base(NOMBRE_PRUEBAS, conectar)
    assert conectar.llamadas == 1
    assert conectar.conexion.sentencias == ["CREATE DATABASE [servia_pruebas]"]
    assert conectar.conexion.cerrada


def test_eliminar_base_con_el_nombre_de_pruebas_cierra_las_conexiones_y_la_elimina():
    """RA-02.4: expulsa las conexiones abiertas (modo de un solo usuario) y elimina solo la base de pruebas."""
    conectar = FabricaDeConexiones()
    proteccion.eliminar_base(NOMBRE_PRUEBAS, conectar)
    assert conectar.llamadas == 1
    (sql,) = conectar.conexion.sentencias
    assert "SINGLE_USER WITH ROLLBACK IMMEDIATE" in sql
    assert "DROP DATABASE [servia_pruebas]" in sql
    assert "IF DB_ID(N'servia_pruebas') IS NOT NULL" in sql  # si no existe, no hace nada
    assert set(re.findall(r"\[([^\]]+)\]", sql)) == {"servia_pruebas"}  # ninguna otra base
    assert conectar.conexion.cerrada


def test_si_el_servidor_rechaza_crear_la_base_aborta_con_un_mensaje_en_espanol_y_cierra_la_conexion():
    """RA-02.4: p. ej. el usuario de SQL Server sin permiso de `CREATE DATABASE`."""
    conexion = ConexionSimulada(error=RuntimeError("CREATE DATABASE permission denied in database 'master'"))
    with pytest.raises(AbortoPruebas) as error:
        proteccion.crear_base(NOMBRE_PRUEBAS, FabricaDeConexiones(conexion))
    mensaje = str(error.value)
    assert "servia_pruebas" in mensaje
    assert "permission denied" in mensaje  # el mensaje del servidor ayuda a quien administra
    assert conexion.cerrada


def test_si_el_servidor_rechaza_eliminar_la_base_aborta_y_cierra_la_conexion():
    conexion = ConexionSimulada(error=RuntimeError("no se pudo"))
    with pytest.raises(AbortoPruebas, match="eliminar"):
        proteccion.eliminar_base(NOMBRE_PRUEBAS, FabricaDeConexiones(conexion))
    assert conexion.cerrada


# --- cadena de conexión -------------------------------------------------------------------------------

def test_la_cadena_de_conexion_protege_los_simbolos_de_la_contrasena():
    """Una contraseña con `;`, `}` o `{` no debe romper la cadena de ODBC ni cambiar otro parámetro."""
    cfg = {"SQL_SERVER_HOST": "servidor-falso", "SQL_SERVER_PORT": "14330", "SQL_SERVER_USER": "usuario_falso",
           "SQL_SERVER_PASSWORD": "a;b}c{d=e", "SQL_SERVER_DRIVER": "Driver Falso 99"}
    cadena = entorno.cadena_de_conexion(cfg, "master")
    assert "DRIVER={Driver Falso 99}" in cadena
    assert "SERVER=servidor-falso,14330" in cadena
    assert "DATABASE=master" in cadena
    assert "PWD={a;b}}c{d=e}" in cadena  # entre llaves y con `}` duplicada
    assert "TrustServerCertificate=yes" in cadena


# --- cerrar -------------------------------------------------------------------------------------------

def test_cerrar_sin_haber_preparado_no_conecta_ni_elimina_nada(monkeypatch):
    """RA-02.4: si la corrida nunca llegó a crear la base, no hay nada que eliminar."""
    monkeypatch.setitem(entorno._estado, "base_creada", False)
    conectar = FabricaDeConexiones()
    entorno.cerrar(conectar)
    assert conectar.llamadas == 0


def test_cerrar_elimina_la_base_de_pruebas_y_es_idempotente(monkeypatch):
    monkeypatch.setitem(entorno._estado, "base_creada", True)
    monkeypatch.setitem(entorno._estado, "nombre", NOMBRE_PRUEBAS)
    monkeypatch.setattr(entorno, "_soltar_motor", lambda: None)
    conectar = FabricaDeConexiones()

    entorno.cerrar(conectar)
    entorno.cerrar(conectar)  # una segunda llamada no vuelve a conectar

    assert conectar.llamadas == 1
    assert "DROP DATABASE [servia_pruebas]" in conectar.conexion.sentencias[0]
    assert entorno._estado["base_creada"] is False


def test_cerrar_elimina_la_base_aunque_soltar_el_motor_falle(monkeypatch):
    """RA-02.4: la base se elimina aunque haya fallos o cortes (el cierre no depende de que todo salga bien)."""
    monkeypatch.setitem(entorno._estado, "base_creada", True)
    monkeypatch.setitem(entorno._estado, "nombre", NOMBRE_PRUEBAS)

    def _falla():
        raise RuntimeError("el motor no se pudo soltar")

    monkeypatch.setattr(entorno, "_soltar_motor", _falla)
    conectar = FabricaDeConexiones()
    with pytest.raises(RuntimeError):
        entorno.cerrar(conectar)
    assert conectar.llamadas == 1  # igual se eliminó
