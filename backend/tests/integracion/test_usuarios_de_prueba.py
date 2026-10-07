"""Pruebas de T8 (spec 002, RA-02.7): usuarios `PRUEBA`, limpieza por prueba y conteo de residuos.

Usan el SQL Server y el Qdrant reales del entorno, pero solo la base y la colección `servia_pruebas`. Cada prueba
limpia lo que crea (fixture automática `registro_de_datos`) y la sesión comprueba al cerrar que no quedó nada
(`pytest_sessionfinish`). Las contraseñas las genera la suite en cada corrida y no se muestran en ninguna salida.
"""
import re

import pytest
from sqlalchemy import text

from tests.soporte import datos, entorno, simulados
from tests.soporte.nombres import NOMBRE_PRUEBAS, PREFIJO_DATOS


def _iniciar_sesion(cliente_api, usuario, contrasena=None):
    return cliente_api.post(
        "/auth/login",
        json={"email": usuario.correo, "password": usuario.contrasena if contrasena is None else contrasena},
    )


def _fila_del_usuario(cedula):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(
            text("SELECT CN_Id_usuario, CT_Contrasenna, CF_Ultimo_acceso, CN_Id_rol, CN_Id_estado "
                 "FROM T_Usuario WHERE CN_Id_usuario = :c"),
            {"c": cedula},
        ).fetchone()


def _bitacoras_del_usuario(cedula):
    from app.db.database import engine

    with engine.connect() as conexion:
        return conexion.execute(
            text("SELECT COUNT(*) FROM T_Bitacora WHERE CN_Id_usuario = :c"), {"c": cedula}
        ).scalar()


# --- Los dos roles inician sesión por la API ---------------------------------------------------------------

def test_el_administrador_inicia_sesion_con_su_rol_y_sin_cambio_de_contrasena(cliente_api, administrador):
    """RA-02.7: `POST /auth/login` con el Administrador de prueba: rol esperado y `requiere_cambio_password` falso."""
    respuesta = _iniciar_sesion(cliente_api, administrador)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["success"] is True
    assert cuerpo["user"]["role"] == "Administrador"
    assert cuerpo["user"]["requiere_cambio_password"] is False
    assert cuerpo["user"]["id"] == administrador.cedula
    assert cuerpo["access_token"]


def test_el_usuario_gubernamental_inicia_sesion_con_su_rol_y_sin_cambio_de_contrasena(cliente_api, usuario_gubernamental):
    """RA-02.7: el Usuario Gubernamental de prueba; su rol conserva el nombre heredado `Usuario Judicial` (RT-06)."""
    respuesta = _iniciar_sesion(cliente_api, usuario_gubernamental)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["user"]["role"] == "Usuario Judicial"
    assert cuerpo["user"]["requiere_cambio_password"] is False
    assert cuerpo["user"]["id"] == usuario_gubernamental.cedula


def test_una_contrasena_equivocada_es_rechazada(cliente_api, administrador):
    """Control: el inicio de sesión de verdad revisa la contraseña (si no, las pruebas anteriores no probarían nada)."""
    assert _iniciar_sesion(cliente_api, administrador, contrasena="otra-contrasena-1").status_code == 401


def test_el_inicio_de_sesion_deja_su_registro_en_la_bitacora_y_la_limpieza_lo_borra(
    cliente_api, administrador, destino_de_pruebas, registro_de_datos
):
    """RF-21, RA-02.7: el inicio de sesión queda en la bitácora de la base de pruebas; la limpieza borra esos registros."""
    assert _iniciar_sesion(cliente_api, administrador).status_code == 200
    assert _bitacoras_del_usuario(administrador.cedula) >= 1

    datos.limpiar(destino_de_pruebas, registro_de_datos)

    assert _bitacoras_del_usuario(administrador.cedula) == 0
    assert _fila_del_usuario(administrador.cedula) is None


# --- La contraseña ----------------------------------------------------------------------------------------------

def test_la_contrasena_se_guarda_con_hash_bcrypt_y_no_en_texto_plano(administrador):
    """RNF-08, RA-02.7: `CT_Contrasenna` es un hash bcrypt que verifica con la contraseña, no la contraseña."""
    from app.repositories.usuario_repository import UsuarioRepository

    fila = _fila_del_usuario(administrador.cedula)

    assert fila.CT_Contrasenna != administrador.contrasena
    assert administrador.contrasena not in fila.CT_Contrasenna
    assert re.match(r"^\$2[aby]\$\d{2}\$", fila.CT_Contrasenna)  # bcrypt, como el sistema real
    assert UsuarioRepository().pwd_context.verify(administrador.contrasena, fila.CT_Contrasenna)


def test_el_usuario_de_prueba_lleva_el_prefijo_prueba_y_el_ultimo_acceso_lleno(administrador, usuario_gubernamental):
    """RA-02.7: todo lo que crea la suite se puede encontrar por su prefijo, y no obliga a cambiar la contraseña."""
    for usuario in (administrador, usuario_gubernamental):
        assert usuario.cedula.startswith(PREFIJO_DATOS) and len(usuario.cedula) <= 20
        assert usuario.nombre_usuario.startswith(PREFIJO_DATOS)
        assert usuario.correo.startswith("prueba") and usuario.correo.endswith(".invalid")
        assert _fila_del_usuario(usuario.cedula).CF_Ultimo_acceso is not None
    assert administrador.cedula != usuario_gubernamental.cedula


def test_la_contrasena_tiene_8_o_mas_caracteres_y_es_distinta_para_cada_usuario(administrador, usuario_gubernamental):
    """RA-02.7: al menos 8 caracteres (RNF-08) y aleatoria: ni repetida entre usuarios ni fija entre corridas."""
    assert len(administrador.contrasena) >= 8 and len(usuario_gubernamental.contrasena) >= 8
    assert administrador.contrasena != usuario_gubernamental.contrasena


def test_el_repr_de_la_contrasena_no_la_muestra(administrador):
    """RA-02.7: ni el `repr` de la contraseña ni el del usuario ni el mensaje de una aserción fallida la muestran."""
    assert administrador.contrasena not in repr(administrador.contrasena)
    assert administrador.contrasena not in repr(administrador)
    with pytest.raises(AssertionError) as error:
        assert administrador.contrasena == "no-es-esta"
    assert administrador.contrasena not in str(error.value)


def test_la_contrasena_no_sale_en_la_salida_ni_en_los_registros_al_iniciar_sesion(
    cliente_api, administrador, usuario_gubernamental, capfd, caplog
):
    """RA-02.7: ni la salida estándar, ni la de errores ni los registros (`logging`) de la corrida traen las contraseñas."""
    caplog.set_level("DEBUG")
    capfd.readouterr()

    assert _iniciar_sesion(cliente_api, administrador).status_code == 200
    assert _iniciar_sesion(cliente_api, usuario_gubernamental).status_code == 200
    assert _iniciar_sesion(cliente_api, administrador, contrasena="otra-contrasena-1").status_code == 401

    salida = capfd.readouterr()
    todo = salida.out + salida.err + caplog.text
    for usuario in (administrador, usuario_gubernamental):
        assert usuario.contrasena not in todo


# --- Una prueba crea una fila, un punto y un archivo y termina -------------------------------------------------------

def test_una_prueba_crea_una_fila_un_punto_y_un_archivo_y_termina(registro_de_datos):
    """RA-02.7: la prueba crea los tres y termina SIN limpiar; la limpieza de la prueba y el conteo de la sesión
    (que falla si algo queda) se encargan, y lo comprueban las corridas hijas de `tests/infraestructura/`."""
    cliente = entorno.cliente_qdrant()
    try:
        usuario = datos.crear_usuario(datos.ROL_ADMINISTRADOR, registro_de_datos)
        punto = datos.crear_punto(cliente, registro_de_datos)
        archivo = registro_de_datos.crear_archivo(
            simulados.carpeta_temporal_de_la_sesion(), f"{PREFIJO_DATOS}_archivo_inventado.txt", b"texto inventado"
        )

        assert _fila_del_usuario(usuario.cedula) is not None
        assert [p.id for p in cliente.retrieve(NOMBRE_PRUEBAS, ids=[punto])] == [punto]
        assert archivo.read_bytes() == b"texto inventado"
    finally:
        cliente.close()


def test_la_limpieza_borra_lo_que_la_prueba_creo_y_el_conteo_de_residuos_da_cero(
    registro_de_datos, destino_de_pruebas
):
    """RA-02.7: con filas, un punto, un archivo y una clave de Redis creados, `contar_residuos` los ve y `limpiar` los quita."""
    usuario = datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    punto = datos.crear_punto(destino_de_pruebas.qdrant, registro_de_datos)
    archivo = registro_de_datos.crear_archivo(
        destino_de_pruebas.carpeta, f"{PREFIJO_DATOS}_otro_archivo.txt", b"texto inventado"
    )
    import redis

    redis.Redis().set("PRUEBA:clave", "1")

    antes = datos.contar_residuos(destino_de_pruebas)
    assert antes.filas["T_Usuario"] == 1
    assert antes.puntos == 1
    assert [a for a in antes.archivos if a.endswith(archivo.name)]
    assert antes.claves_redis >= 1

    datos.limpiar(destino_de_pruebas, registro_de_datos)

    despues = datos.contar_residuos(destino_de_pruebas)
    assert despues.total == 0, despues.texto()
    assert _fila_del_usuario(usuario.cedula) is None
    assert not archivo.exists()
    assert destino_de_pruebas.qdrant.retrieve(NOMBRE_PRUEBAS, ids=[punto]) == []


def test_el_destino_de_pruebas_apunta_a_la_base_y_a_la_coleccion_de_pruebas(destino_de_pruebas):
    """RA-02.3, RA-02.7: la limpieza real solo puede apuntar a `servia_pruebas` y a la carpeta temporal de la suite."""
    assert destino_de_pruebas.base == NOMBRE_PRUEBAS
    assert destino_de_pruebas.coleccion == NOMBRE_PRUEBAS
    assert destino_de_pruebas.carpeta.name.startswith("servia_pruebas_")


# --- Los catálogos de las migraciones ----------------------------------------------------------------------------------

def test_los_catalogos_de_las_migraciones_siguen_completos_tras_crear_y_limpiar(registro_de_datos, destino_de_pruebas):
    """RA-02.7: la limpieza no toca roles, estados ni tipos de acción: siguen con lo que sembraron las migraciones."""
    datos.crear_usuario(datos.ROL_ADMINISTRADOR, registro_de_datos)
    datos.limpiar(destino_de_pruebas, registro_de_datos)

    from app.db.database import engine

    def nombres(consulta):
        with engine.connect() as conexion:
            return set(conexion.execute(text(consulta)).scalars().all())

    assert nombres("SELECT CT_Nombre_rol FROM T_Rol") == {"Administrador", "Usuario Judicial"}
    assert nombres("SELECT CT_Nombre_estado FROM T_Estado") == {"Activo", "Inactivo"}
    assert nombres("SELECT CT_Nombre_estado FROM T_Estado_procesamiento") == {"Pendiente", "Procesado", "Error"}
    assert {"Login", "Logout", "Consulta RAG"} <= nombres("SELECT CT_Nombre_tipo_accion FROM T_Tipo_accion")
    with engine.connect() as conexion:
        assert conexion.execute(text("SELECT COUNT(*) FROM T_Tipo_accion")).scalar() == 15
    assert datos.comparar_catalogos(datos.catalogos_iniciales(), datos.contar_catalogos(destino_de_pruebas.contar)) == []


def test_ninguna_prueba_depende_de_otra_los_nombres_de_los_usuarios_no_se_repiten(registro_de_datos):
    """RA-02.7: cada usuario creado tiene cédula, nombre y correo propios, así que el orden de las pruebas no importa."""
    usuarios = [datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos) for _ in range(3)]
    assert len({u.cedula for u in usuarios}) == len({u.nombre_usuario for u in usuarios}) == len({u.correo for u in usuarios}) == 3
    assert len(set(registro_de_datos.usuarios)) == 3


def test_crear_usuario_con_un_rol_desconocido_falla_sin_crear_nada(registro_de_datos):
    with pytest.raises(ValueError, match="rol"):
        datos.crear_usuario("Superusuario", registro_de_datos)
    assert registro_de_datos.usuarios == []


def test_el_conteo_del_cierre_detecta_un_catalogo_alterado_y_un_residuo(registro_de_datos, destino_de_pruebas):
    """RA-02.7: el conteo que corre al cerrar la sesión (`contar_residuos_de_la_sesion`) falla si un catálogo de las
    migraciones cambió o si quedó una fila `PRUEBA`; con todo limpio, da cero. Se altera un catálogo a propósito (solo
    en la base de pruebas) y se restaura en `finally`."""
    from app.db.database import engine

    assert not datos.contar_residuos_de_la_sesion().hay  # punto de partida: nada que limpiar ni alterado

    usuario = datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    with engine.begin() as conexion:
        conexion.execute(text("INSERT INTO T_Estado (CT_Nombre_estado) VALUES (N'PRUEBA_catalogo_alterado')"))
    try:
        residuos = datos.contar_residuos_de_la_sesion()
        assert residuos.hay
        assert residuos.filas["T_Usuario"] == 1  # la fila que esta prueba aún no limpió
        assert len(residuos.catalogos) == 1 and "T_Estado" in residuos.catalogos[0]
        assert "catálogos de las migraciones alterados" in residuos.texto()
        assert any("quedaron datos de prueba sin limpiar" in linea for linea in datos.lineas_de_residuos())
    finally:
        with engine.begin() as conexion:
            conexion.execute(text("DELETE FROM T_Estado WHERE CT_Nombre_estado = N'PRUEBA_catalogo_alterado'"))
        datos.limpiar(destino_de_pruebas, registro_de_datos)

    assert _fila_del_usuario(usuario.cedula) is None
    despues = datos.contar_residuos_de_la_sesion()
    assert not despues.hay, despues.texto()
    assert datos.lineas_de_residuos() == ["Residuos de datos de prueba al cerrar la sesión: ninguno"]


def test_la_limpieza_respeta_el_orden_de_claves_foraneas_con_filas_en_las_seis_tablas(registro_de_datos, destino_de_pruebas):
    """RA-02.7: con filas `PRUEBA` en las seis tablas (usuario, notebook, tema, documento, su enlace y bitácora de las
    tres formas), `limpiar` las borra sin violar ninguna clave foránea y el conteo de residuos queda en cero."""
    from app.db.database import SessionLocal
    from app.db.models import T_Bitacora, T_Documento, T_Estado_procesamiento, T_Expediente, T_Notebook

    usuario = datos.crear_usuario(datos.ROL_USUARIO_GUBERNAMENTAL, registro_de_datos)
    with SessionLocal() as db:
        estado = db.query(T_Estado_procesamiento).first()
        tema = T_Expediente(CT_Num_expediente=f"{PREFIJO_DATOS}-TEMA-FK")
        documento = T_Documento(CT_Nombre_archivo=f"{PREFIJO_DATOS}_documento.txt", CT_Tipo_archivo="txt",
                                CN_Id_estado=estado.CN_Id_estado)
        tema.documentos.append(documento)
        db.add_all([
            tema,
            T_Notebook(CT_Nombre=f"{PREFIJO_DATOS} notebook", CN_Id_usuario=usuario.cedula),
        ])
        db.flush()
        db.add_all([
            T_Bitacora(CT_Texto="acción del usuario", CN_Id_usuario=usuario.cedula, CN_Id_tipo_accion=3),
            T_Bitacora(CT_Texto="acción sobre el tema", CN_Id_expediente=tema.CN_Id_expediente, CN_Id_tipo_accion=2),
            T_Bitacora(CT_Texto=f"{PREFIJO_DATOS}: registro sin usuario ni tema", CN_Id_tipo_accion=3),
        ])
        db.commit()

    antes = datos.contar_residuos(destino_de_pruebas)
    assert antes.filas == {
        "T_Bitacora": 3, "T_Notebook": 1, "T_Expediente_Documento": 1, "T_Documento": 1, "T_Expediente": 1, "T_Usuario": 1,
    }

    datos.limpiar(destino_de_pruebas, registro_de_datos)

    despues = datos.contar_residuos(destino_de_pruebas)
    assert despues.total == 0, despues.texto()
