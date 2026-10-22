"""Lanzador de la instancia de extremo a extremo (spec 005a, RA-02.40, RA-02.41 y RA-02.49).

    python -m tests.instancia_e2e            arranca la instancia en el puerto 8100 (y no termina hasta apagarla)
    python -m tests.instancia_e2e --apagar   apaga la instancia que esté en marcha

Flujo del arranque: fija el nombre `servia_pruebas_e2e` por código, arma la configuración (variables de entorno antes de
importar nada de `app`, porque `database.py` se conecta al importarse), crea la carpeta temporal en `/tmp`, reemplaza la
base y la colección de pruebas e2e, simula Redis, Ollama, HTR, audio y correo, importa la aplicación real (`main.py`), le
suma el router de control y la sirve con uvicorn sin recarga automática. Al terminar elimina la base, la colección y la
carpeta temporal. El token del control se escribe en un archivo 0600 de esa carpeta; nunca se imprime.
"""
import contextlib
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from typing import Optional

sys.dont_write_bytecode = True  # ningún .pyc nuevo bajo `/app` (el servidor de desarrollo vigila esa carpeta)

from tests.instancia_e2e import configuracion as cfg_e2e
from tests.instancia_e2e import control
from tests.instancia_e2e.simulados_e2e import (
    LIMITE_INACTIVIDAD_SEGUNDOS, Vigilante, destino_de_la_instancia, instalar_almacen_controlable, instalar_controles,
    instalar_simulados, leer_usuarios_sembrados,
)
from tests.soporte import configuracion, entorno, proteccion, simulados
from tests.soporte.nombres import NOMBRE_PRUEBAS_E2E
from tests.soporte.proteccion import AbortoPruebas

# Dónde queda, fuera de la carpeta temporal (que se elimina al salir), el registro de una instancia que terminó mal.
REGISTRO_DEL_ULTIMO_ERROR = Path(cfg_e2e.CARPETA_E2E.parent) / "servia_e2e_ultimo_error.log"


def _vivo(pid: int) -> bool:
    """¿Sigue en marcha el proceso `pid`? Un proceso zombi (terminó y nadie lo recogió) cuenta como terminado."""
    try:
        estado = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
        return estado != "Z"
    except (OSError, IndexError):
        pass
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _leer_pid(carpeta: Path) -> Optional[int]:
    try:
        return int((carpeta / "pid").read_text().strip())
    except (OSError, ValueError):
        return None


def apagar_instancia(carpeta: Path = cfg_e2e.CARPETA_E2E, espera: float = 60.0) -> bool:
    """Pide a la instancia (por su PID) que termine y espera a que lo haga; True si había una en marcha.

    Sin archivo de PID, o con el PID de un proceso que ya no existe, no hace nada y devuelve False. Si la instancia no
    termina en `espera` segundos, aborta: su cierre elimina la base y la colección, y no se da por apagada sin eso.
    """
    pid = _leer_pid(Path(carpeta))
    if pid is None or not _vivo(pid):
        return False
    os.kill(pid, signal.SIGTERM)
    limite = time.monotonic() + espera
    while _vivo(pid):
        if time.monotonic() >= limite:
            raise AbortoPruebas(f"La instancia de extremo a extremo (PID {pid}) no terminó en {espera:g} segundos.")
        time.sleep(0.2)
    return True


def _redirigir_salida(archivo: Path) -> None:
    """Manda la salida estándar y de error al registro de la instancia (`docker compose exec -d` la descartaría)."""
    descriptor = os.open(archivo, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(descriptor, 1)
    os.dup2(descriptor, 2)
    os.close(descriptor)


def _escribir_privado(archivo: Path, texto: str) -> None:
    descriptor = os.open(archivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as salida:
        salida.write(texto)


def _guardar_registro_del_error(carpeta: Path) -> None:
    """Conserva (sin secretos) el registro de una instancia que terminó mal, porque la carpeta se elimina al salir."""
    try:
        texto = entorno._sin_secretos((carpeta / "instancia.log").read_text(errors="replace"))
        REGISTRO_DEL_ULTIMO_ERROR.write_text(texto[-20000:])
        REGISTRO_DEL_ULTIMO_ERROR.chmod(0o600)
    except OSError:
        pass


def arrancar() -> int:
    """Arranca la instancia y la sirve hasta que se apague; devuelve el código de salida."""
    os.chdir(cfg_e2e.RAIZ_BACKEND)  # `main.py` crea `uploads` en la carpeta actual
    carpeta = cfg_e2e.CARPETA_E2E

    pid_anterior = _leer_pid(carpeta)
    if pid_anterior is not None and _vivo(pid_anterior):
        print(f"Ya hay una instancia de extremo a extremo en marcha (PID {pid_anterior}). Use --apagar.")
        return 1

    proteccion.fijar_nombre_activo(NOMBRE_PRUEBAS_E2E)
    configuracion.exigir_sin_modulos_importados()
    cfg = cfg_e2e.construir_configuracion_e2e(configuracion.leer_configuracion_desarrollo())
    cfg_e2e.preparar_carpeta(carpeta)
    _escribir_privado(carpeta / "pid", str(os.getpid()))
    _redirigir_salida(carpeta / "instancia.log")

    import secrets

    import uvicorn

    codigo = 0
    controles = None
    vigilante = Vigilante(LIMITE_INACTIVIDAD_SEGUNDOS)
    pila = contextlib.ExitStack()
    try:
        configuracion.aplicar(cfg)
        simulados.instalar_redis_simulado()
        entorno.preparar()
        entorno.preparar_coleccion()
        piezas = instalar_simulados()

        import main  # la aplicación real; su arranque carga los embeddings y comprueba Qdrant

        # Archivos y avatares fuera de `uploads/`: en una subcarpeta de la carpeta temporal, que la limpieza vacía por prueba.
        carpeta_de_archivos = pila.enter_context(simulados.desviar_carpetas())
        almacen = instalar_almacen_controlable(piezas["parches"])  # la recuperación obedece al control (T5)
        controles = instalar_controles(piezas)  # motor, ingesta en el proceso y notebooks controlables (T6)
        destino = destino_de_la_instancia(
            [carpeta_de_archivos / "uploads", carpeta_de_archivos / "avatares"], piezas["correo"], leer_usuarios_sembrados(),
            almacen, controles,
        )

        token = secrets.token_urlsafe(32)
        _escribir_privado(carpeta / "control.token", token)
        servidor = uvicorn.Server(uvicorn.Config(main.app, host="0.0.0.0", port=cfg_e2e.PUERTO_E2E, log_level="info"))

        def apagar() -> None:
            servidor.should_exit = True

        control.configurar(control.Contexto(
            token=token, apagar=apagar, vigilante=vigilante, registro=carpeta / "instancia.log", destino=destino,
            correo=piezas["correo"], almacen=almacen, controles=controles,
        ))
        main.app.include_router(control.router)

        # uvicorn vuelve a lanzar la señal que lo detuvo al terminar; con un manejador propio no mata el proceso antes
        # de que el cierre (más abajo) elimine la base, la colección y la carpeta.
        for senal in (signal.SIGTERM, signal.SIGINT):
            signal.signal(senal, lambda *_: None)

        vigilante.iniciar(apagar)
        print(f"Instancia de extremo a extremo lista en el puerto {cfg_e2e.PUERTO_E2E} (base {NOMBRE_PRUEBAS_E2E}).", flush=True)
        servidor.run()
        if not servidor.started:
            print("La instancia de extremo a extremo no pudo arrancar.", flush=True)
            codigo = 3
    except BaseException as error:
        codigo = 2
        import traceback

        print(f"Se aborta la instancia de extremo a extremo ({type(error).__name__}): {entorno._sin_secretos(str(error))[:500]}", flush=True)
        traceback.print_exc()
    finally:
        vigilante.detener()
        if controles is not None:  # nada retenido y el hilo de la ingesta terminado, antes de eliminar la base
            try:
                controles.cerrar()
            except Exception as error:
                print(f"No se pudo cerrar la ingesta de la instancia ({type(error).__name__}).", flush=True)
        pila.close()
        try:
            entorno.cerrar()
        except Exception as error:
            print(f"No se pudo eliminar la base o la colección ({type(error).__name__}); la siguiente corrida las reemplaza.", flush=True)
            codigo = codigo or 2
        if codigo != 0:
            _guardar_registro_del_error(carpeta)
        sys.stdout.flush()
        sys.stderr.flush()
        simulados.eliminar_carpeta_temporal()
        shutil.rmtree(carpeta, ignore_errors=True)
    return codigo


def principal(argumentos: list) -> int:
    if "--apagar" in argumentos:
        try:
            if apagar_instancia():
                print("Instancia de extremo a extremo apagada.")
            else:
                print("No hay ninguna instancia de extremo a extremo en marcha.")
        except AbortoPruebas as aborto:
            print(str(aborto))
            return 1
        return 0
    try:
        return arrancar()
    except AbortoPruebas as aborto:
        print(str(aborto))
        return 2


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
