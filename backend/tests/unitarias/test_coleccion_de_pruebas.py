"""Pruebas de T5 (spec 002, RA-02.3, RA-02.4 y RA-02.6): la colección de Qdrant de pruebas y la espera de servicios.

Ninguna abre una conexión real: el cliente de Qdrant, el servidor de Tika y el reloj son simulados, y
el guardián de las unitarias frena cualquier intento de usar Qdrant de verdad.
"""
import os
import socket

import pytest

from tests.soporte import entorno, proteccion
from tests.soporte.nombres import ESPERA_SERVICIOS_SEGUNDOS, NOMBRE_PRUEBAS
from tests.soporte.proteccion import AbortoPruebas
from tests.soporte.simulados import ServicioRealProhibido

# Nombres que el punto de DDL de colecciones debe rechazar sin conectarse (los de la protección, RA-02.3).
NOMBRES_INVALIDOS = [
    pytest.param("justicia_docs", id="coleccion-de-desarrollo"),
    pytest.param("db_ServIA", id="base-de-desarrollo"),
    pytest.param("SERVIA_PRUEBAS", id="mayusculas"),
    pytest.param("Servia_Pruebas", id="mayuscula-inicial"),
    pytest.param("mi_servia_pruebas", id="lo-contiene-antes"),
    pytest.param("servia_pruebas_2", id="lo-contiene-despues"),
    pytest.param(" servia_pruebas", id="espacio-al-inicio"),
    pytest.param("", id="vacio"),
    pytest.param("servia_pruebas/../justicia_docs", id="ruta"),
    pytest.param("servia_pruebas; DROP", id="inyeccion"),
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


class QdrantSimulado:
    """Ocupa el lugar de `QdrantClient`: registra cada llamada y qué colecciones «existen»."""

    def __init__(self, existentes=(), error=None):
        self.existentes = set(existentes)
        self.llamadas = []
        self.cerrado = False
        self._error = error

    def _registrar(self, operacion, **datos):
        self.llamadas.append((operacion, datos))
        if self._error is not None:
            raise self._error

    def get_collections(self):
        self._registrar("get_collections")
        return object()

    def collection_exists(self, collection_name):
        self._registrar("collection_exists", nombre=collection_name)
        return collection_name in self.existentes

    def create_collection(self, collection_name, vectors_config=None, **kwargs):
        self._registrar("create_collection", nombre=collection_name, vectores=vectors_config)
        self.existentes.add(collection_name)

    def delete_collection(self, collection_name, **kwargs):
        self._registrar("delete_collection", nombre=collection_name)
        self.existentes.discard(collection_name)

    def close(self):
        self.cerrado = True

    def llamadas_a(self, nombre):
        return [datos for llamada, datos in self.llamadas if llamada == nombre]


class FabricaDeClientes:
    """`conectar()` de mentira: cuenta las veces que se llama y entrega el cliente simulado."""

    def __init__(self, cliente=None):
        self.llamadas = 0
        self.cliente = cliente or QdrantSimulado()

    def __call__(self):
        self.llamadas += 1
        return self.cliente


@pytest.fixture
def estado_limpio(monkeypatch):
    """Cada prueba parte sin colección marcada como creada y deja el estado de la sesión como estaba."""
    monkeypatch.setitem(entorno._estado, "coleccion_creada", False)
    monkeypatch.setitem(entorno._estado, "base_creada", False)


# --- crear_coleccion y eliminar_coleccion: el único punto de DDL de colecciones (RA-02.3, RA-02.4) ---------

@pytest.mark.parametrize("funcion", [
    pytest.param(lambda nombre, conectar: proteccion.crear_coleccion(nombre, conectar, 1024), id="crear_coleccion"),
    pytest.param(lambda nombre, conectar: proteccion.eliminar_coleccion(nombre, conectar), id="eliminar_coleccion"),
])
@pytest.mark.parametrize("nombre", NOMBRES_INVALIDOS)
def test_el_punto_de_ddl_de_colecciones_se_niega_con_un_nombre_invalido_sin_conectarse(funcion, nombre):
    """RA-02.3: con cualquier nombre que no sea el de pruebas (incluida `justicia_docs`), aborta ANTES de crear el cliente."""
    conectar = FabricaDeClientes()
    with pytest.raises(AbortoPruebas):
        funcion(nombre, conectar)
    assert conectar.llamadas == 0
    assert conectar.cliente.llamadas == []


def test_crear_coleccion_crea_solo_la_de_pruebas_con_la_dimension_y_distancia_coseno():
    """RA-02.4: una sola creación, con el nombre de pruebas, el tamaño pedido y la distancia coseno del sistema."""
    from qdrant_client.models import Distance

    conectar = FabricaDeClientes()
    proteccion.crear_coleccion(NOMBRE_PRUEBAS, conectar, 1024)

    assert conectar.llamadas == 1
    (creacion,) = conectar.cliente.llamadas_a("create_collection")
    assert creacion["nombre"] == "servia_pruebas"
    assert creacion["vectores"].size == 1024
    assert creacion["vectores"].distance == Distance.COSINE
    assert [llamada for llamada, _ in conectar.cliente.llamadas] == ["create_collection"]  # nada más
    assert conectar.cliente.cerrado


@pytest.mark.parametrize("dimension", [0, -1, 1.5, "1024", None])
def test_crear_coleccion_se_niega_con_una_dimension_invalida_sin_crear_nada(dimension):
    conectar = FabricaDeClientes()
    with pytest.raises(AbortoPruebas, match="dimensi"):
        proteccion.crear_coleccion(NOMBRE_PRUEBAS, conectar, dimension)
    assert conectar.cliente.llamadas == []


def test_eliminar_coleccion_elimina_solo_la_de_pruebas_si_existe():
    """RA-02.4: consulta si existe y, solo entonces, elimina esa colección y ninguna otra."""
    conectar = FabricaDeClientes(QdrantSimulado(existentes={"servia_pruebas", "justicia_docs"}))
    proteccion.eliminar_coleccion(NOMBRE_PRUEBAS, conectar)

    assert conectar.cliente.llamadas_a("delete_collection") == [{"nombre": "servia_pruebas"}]
    assert conectar.cliente.existentes == {"justicia_docs"}  # la otra no se tocó
    assert conectar.cliente.cerrado


def test_eliminar_coleccion_que_no_existe_no_hace_nada():
    conectar = FabricaDeClientes(QdrantSimulado(existentes={"justicia_docs"}))
    proteccion.eliminar_coleccion(NOMBRE_PRUEBAS, conectar)
    assert conectar.cliente.llamadas_a("delete_collection") == []
    assert conectar.cliente.cerrado


@pytest.mark.parametrize("accion", [
    pytest.param(lambda conectar: proteccion.crear_coleccion(NOMBRE_PRUEBAS, conectar, 1024), id="crear"),
    pytest.param(lambda conectar: proteccion.eliminar_coleccion(NOMBRE_PRUEBAS, conectar), id="eliminar"),
])
def test_si_qdrant_rechaza_la_operacion_aborta_con_un_mensaje_en_espanol_y_cierra_el_cliente(accion):
    """RA-02.4: el error del servidor se convierte en un aborto que nombra Qdrant y la colección."""
    cliente = QdrantSimulado(existentes={"servia_pruebas"}, error=RuntimeError("operación rechazada por el servidor"))
    with pytest.raises(AbortoPruebas) as error:
        accion(FabricaDeClientes(cliente))
    mensaje = str(error.value)
    assert "Qdrant" in mensaje and "servia_pruebas" in mensaje
    assert "Se aborta la suite de pruebas" in mensaje
    assert cliente.cerrado


# --- esperar Qdrant y Tika (RA-02.4) -----------------------------------------------------------------------

def test_esperar_qdrant_sigue_intentando_hasta_que_responde_al_tercer_intento():
    tiempo = RelojSimulado()
    cliente = QdrantSimulado()
    intentos = []

    def conectar():
        intentos.append(1)
        if len(intentos) < 3:
            raise ConnectionError("todavía arrancando")
        return cliente

    entorno.esperar_qdrant(conectar, reloj=tiempo.reloj, pausa=tiempo.pausa)

    assert len(intentos) == 3
    assert len(tiempo.pausas) == 2
    assert cliente.cerrado  # la consulta de comprobación no deja el cliente abierto


def test_esperar_qdrant_que_nunca_responde_aborta_a_los_60_segundos_y_nombra_el_servicio():
    """RA-02.4: pasados 60 s (de reloj simulado) aborta con un mensaje en español que dice que Qdrant no respondió."""
    tiempo = RelojSimulado()
    inicio = tiempo.reloj()

    def conectar():
        raise ConnectionError("nunca responde")

    with pytest.raises(AbortoPruebas) as error:
        entorno.esperar_qdrant(conectar, reloj=tiempo.reloj, pausa=tiempo.pausa)

    mensaje = str(error.value)
    assert "Qdrant" in mensaje and "60" in mensaje and "no respondi" in mensaje.lower()
    assert tiempo.reloj() - inicio >= ESPERA_SERVICIOS_SEGUNDOS


def test_esperar_tika_sigue_intentando_hasta_que_responde_al_tercer_intento():
    tiempo = RelojSimulado()
    intentos = []

    def preguntar():
        intentos.append(1)
        if len(intentos) < 3:
            raise ConnectionError("todavía arrancando")

    entorno.esperar_tika(preguntar, reloj=tiempo.reloj, pausa=tiempo.pausa)
    assert len(intentos) == 3


def test_esperar_tika_que_nunca_responde_aborta_a_los_60_segundos_y_nombra_el_servicio():
    """RA-02.4: lo mismo para Tika (el mensaje nombra Tika, no otro servicio)."""
    tiempo = RelojSimulado()
    inicio = tiempo.reloj()

    def preguntar():
        raise ConnectionError("nunca responde")

    with pytest.raises(AbortoPruebas) as error:
        entorno.esperar_tika(preguntar, reloj=tiempo.reloj, pausa=tiempo.pausa)

    mensaje = str(error.value)
    assert "Tika" in mensaje and "60" in mensaje and "no respondi" in mensaje.lower()
    assert "Qdrant" not in mensaje
    assert tiempo.reloj() - inicio >= ESPERA_SERVICIOS_SEGUNDOS


def test_pedir_a_tika_consulta_la_direccion_del_sistema_y_exige_un_200(monkeypatch):
    """La comprobación usa `TIKA_SERVER_URL` (el Tika real, que solo usa la integración) y falla si no responde 200."""
    import requests

    pedidas = []

    class Respuesta:
        def __init__(self, codigo):
            self.status_code = codigo

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.HTTPError(f"código {self.status_code}")

    codigos = iter([200, 503])
    monkeypatch.setattr(requests, "get", lambda url, **kwargs: pedidas.append((url, kwargs)) or Respuesta(next(codigos)))

    entorno.pedir_a_tika("http://tika-simulado.invalid:9998")
    with pytest.raises(requests.HTTPError):
        entorno.pedir_a_tika("http://tika-simulado.invalid:9998")

    assert [url for url, _ in pedidas] == ["http://tika-simulado.invalid:9998/tika"] * 2
    assert all(kwargs["timeout"] == entorno.ESPERA_POR_INTENTO for _, kwargs in pedidas)


# --- preparar y cerrar la colección (RA-02.4) --------------------------------------------------------------

def test_preparar_coleccion_la_crea_con_dim_y_coseno_y_queda_marcada_para_cerrarse(estado_limpio):
    from qdrant_client.models import Distance

    conectar = FabricaDeClientes()
    entorno.preparar_coleccion(conectar)

    (creacion,) = conectar.cliente.llamadas_a("create_collection")
    assert creacion["nombre"] == "servia_pruebas"
    assert creacion["vectores"].size == int(os.environ["DIM"]) == 1024
    assert creacion["vectores"].distance == Distance.COSINE
    assert entorno._estado["coleccion_creada"] is True


def test_preparar_coleccion_reemplaza_la_que_dejo_una_corrida_cortada(estado_limpio):
    """RA-02.4: el nombre es siempre el mismo, así que una colección anterior (aquí, de otro tamaño) se elimina y se recrea."""
    conectar = FabricaDeClientes(QdrantSimulado(existentes={"servia_pruebas"}))
    entorno.preparar_coleccion(conectar)

    pasos = [llamada for llamada, _ in conectar.cliente.llamadas if llamada in ("delete_collection", "create_collection")]
    assert pasos == ["delete_collection", "create_collection"]
    assert conectar.cliente.existentes == {"servia_pruebas"}


def test_preparar_coleccion_aborta_sin_conectarse_si_el_nombre_del_entorno_no_es_el_de_pruebas(estado_limpio, monkeypatch):
    """RA-02.3: valida lo que está en el entorno ANTES de crear el cliente; no toca `justicia_docs`."""
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "justicia_docs")
    conectar = FabricaDeClientes(QdrantSimulado(existentes={"justicia_docs"}))
    with pytest.raises(AbortoPruebas, match="justicia_docs"):
        entorno.preparar_coleccion(conectar)
    assert conectar.llamadas == 0
    assert conectar.cliente.existentes == {"justicia_docs"}
    assert entorno._estado["coleccion_creada"] is False


def test_preparar_coleccion_aborta_si_el_modulo_de_qdrant_del_sistema_ya_tomo_otro_nombre(estado_limpio, monkeypatch):
    """RA-02.3: también el valor que ya importó el sistema (`qdrant_backend.QDRANT_COLLECTION_NAME`)."""
    import sys
    import types

    falso = types.ModuleType("app.vectorstore.qdrant_backend")
    falso.QDRANT_COLLECTION_NAME = "justicia_docs"
    monkeypatch.setitem(sys.modules, "app.vectorstore.qdrant_backend", falso)
    conectar = FabricaDeClientes()
    with pytest.raises(AbortoPruebas, match="justicia_docs"):
        entorno.preparar_coleccion(conectar)
    assert conectar.llamadas == 0


def test_cerrar_coleccion_la_elimina_y_es_idempotente(estado_limpio, monkeypatch):
    monkeypatch.setitem(entorno._estado, "coleccion_creada", True)
    conectar = FabricaDeClientes(QdrantSimulado(existentes={"servia_pruebas", "justicia_docs"}))

    entorno.cerrar_coleccion(conectar)
    entorno.cerrar_coleccion(conectar)  # la segunda no vuelve a conectar

    assert conectar.llamadas == 1
    assert conectar.cliente.existentes == {"justicia_docs"}
    assert entorno._estado["coleccion_creada"] is False


def test_cerrar_coleccion_sin_haberla_creado_no_conecta(estado_limpio):
    conectar = FabricaDeClientes()
    entorno.cerrar_coleccion(conectar)
    assert conectar.llamadas == 0


def test_si_no_se_puede_eliminar_la_coleccion_queda_marcada_para_reintentar(estado_limpio, monkeypatch):
    monkeypatch.setitem(entorno._estado, "coleccion_creada", True)
    cliente = QdrantSimulado(existentes={"servia_pruebas"}, error=RuntimeError("Qdrant detenido"))
    with pytest.raises(AbortoPruebas):
        entorno.cerrar_coleccion(FabricaDeClientes(cliente))
    assert entorno._estado["coleccion_creada"] is True


def test_cerrar_elimina_la_coleccion_y_despues_la_base(monkeypatch):
    """RA-02.4: el cierre de la sesión elimina la colección (si se creó) y la base, en ese orden."""
    monkeypatch.setitem(entorno._estado, "coleccion_creada", True)
    monkeypatch.setitem(entorno._estado, "base_creada", True)
    monkeypatch.setitem(entorno._estado, "nombre", NOMBRE_PRUEBAS)
    monkeypatch.setattr(entorno, "_soltar_motor", lambda: None)
    orden = []

    class ConexionBase:
        def execute(self, sql, *args):
            orden.append("base")

        def close(self):
            pass

    class ClienteQdrant(QdrantSimulado):
        def delete_collection(self, collection_name, **kwargs):
            orden.append("coleccion")
            super().delete_collection(collection_name, **kwargs)

    entorno.cerrar(lambda: ConexionBase(), FabricaDeClientes(ClienteQdrant(existentes={"servia_pruebas"})))

    assert orden == ["coleccion", "base"]


def test_si_qdrant_no_responde_al_cerrar_la_base_de_pruebas_igual_se_elimina(monkeypatch):
    """RA-02.4: con Qdrant detenido, el cierre falla diciendo por qué, pero la base de pruebas se elimina de todos modos."""
    monkeypatch.setitem(entorno._estado, "coleccion_creada", True)
    monkeypatch.setitem(entorno._estado, "base_creada", True)
    monkeypatch.setitem(entorno._estado, "nombre", NOMBRE_PRUEBAS)
    monkeypatch.setattr(entorno, "_soltar_motor", lambda: None)
    sentencias = []

    class ConexionBase:
        def execute(self, sql, *args):
            sentencias.append(sql)

        def close(self):
            pass

    qdrant_detenido = QdrantSimulado(existentes={"servia_pruebas"}, error=ConnectionError("Qdrant detenido"))
    with pytest.raises(AbortoPruebas, match="Qdrant"):
        entorno.cerrar(lambda: ConexionBase(), FabricaDeClientes(qdrant_detenido))

    assert len(sentencias) == 1 and "DROP DATABASE [servia_pruebas]" in sentencias[0]
    assert entorno._estado["base_creada"] is False


# --- preparar el entorno de integración ----------------------------------------------------------------------

def test_preparar_integracion_espera_a_qdrant_y_a_tika_y_despues_crea_la_coleccion(estado_limpio):
    """RA-02.4: orden de la fixture `entorno_integracion`: Qdrant, Tika y, con ambos arriba, la colección."""
    pasos = []
    cliente = QdrantSimulado()

    def conectar():
        pasos.append("qdrant")
        return cliente

    entorno.preparar_integracion(conectar_qdrant=conectar, preguntar_tika=lambda: pasos.append("tika"))

    assert pasos[:2] == ["qdrant", "tika"]  # primero se espera a los dos servicios...
    assert set(pasos[2:]) == {"qdrant"}  # ...y después solo se trabaja con Qdrant
    assert cliente.llamadas_a("create_collection")


def test_si_tika_no_responde_la_coleccion_no_llega_a_crearse(estado_limpio):
    tiempo = RelojSimulado()
    cliente = QdrantSimulado()

    def preguntar():
        raise ConnectionError("Tika detenido")

    with pytest.raises(AbortoPruebas, match="Tika"):
        entorno.preparar_integracion(conectar_qdrant=lambda: cliente, preguntar_tika=preguntar,
                                     reloj=tiempo.reloj, pausa=tiempo.pausa)
    assert cliente.llamadas_a("create_collection") == []
    assert entorno._estado["coleccion_creada"] is False


# --- el guardián de las unitarias sigue frenando a Qdrant real (RA-02.6) -------------------------------------

def test_el_cliente_de_qdrant_de_la_suite_no_se_puede_crear_en_una_unitaria(guardian_servicios):
    """RA-02.6: aunque `entorno` tenga el cliente real, una prueba unitaria no puede usarlo."""
    with pytest.raises(ServicioRealProhibido, match="Qdrant"):
        entorno.cliente_qdrant()
    assert guardian_servicios.intentos == ["Qdrant"]
    guardian_servicios.reconocer()
