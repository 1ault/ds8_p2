"""Arranque del backend: MQTT, SQLite, nube, panel y tareas de mantenimiento.

Uso:
    python -m backend.main                 # arranca con .env o valores por defecto
    python -m backend.main --seed          # ademas carga datos de demostracion
    python -m backend.main --sin-login     # panel abierto (modo demostracion)
    python -m backend.main --puerto 8010
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time
from pathlib import Path

from aiohttp import web

from . import VERSION
from . import cloud as cloud_mod
from . import commands as commands_mod
from . import config as config_mod
from .bus import Hub
from .mqtt_bridge import PuenteMqtt, decodificar
from .storage import Almacen, iso, ahora_utc
from .web.app import crear_app

RAIZ = Path(__file__).resolve().parent.parent
RUTA_SEED = RAIZ / "sql" / "seed.sql"


def log(mensaje: str) -> None:
    print("[%s] %s" % (time.strftime("%H:%M:%S"), mensaje), flush=True)


class Backend:
    """Compone todos los servicios y orquesta las tareas de fondo."""

    def __init__(self, cfg: config_mod.Config, logger=log, sin_mqtt: bool = False):
        self.cfg = cfg
        self.log = logger
        self.sin_mqtt = sin_mqtt

        self.almacen = Almacen(cfg.ruta_bd)
        self.hub = Hub()
        self.puente = PuenteMqtt(cfg, log=logger)
        self.nube = (cloud_mod.NubeThingSpeak(cfg, log=logger)
                     if cfg.nube_activa else cloud_mod.NubeNula())
        self.comandos = commands_mod.ServicioComandos(
            cfg, self.almacen, self.puente, hub=self.hub, log=logger
        )
        self.app = crear_app(cfg, self.almacen, self.hub, self.comandos,
                             self.nube, self.puente, log=logger, version=VERSION)

        self._runner: web.AppRunner | None = None
        self.tareas: list[asyncio.Task] = []
        self.estado_nodo = "desconocido"
        self.ultimo_estado_seguridad: str | None = None
        self.lecturas_guardadas = 0
        self.eventos_guardados = 0
        self._parar = asyncio.Event()

    # -- arranque ----------------------------------------------------------
    async def arrancar(self) -> None:
        await self.almacen.abrir()
        await self.almacen.registrar_dispositivo(
            self.cfg.device_id, nombre="Centinela - Puerta principal",
            ubicacion="Casa", firmware="2.0.0",
        )
        self.log("base de datos lista en %s" % self.cfg.ruta_bd)

        conectado = False
        if self.sin_mqtt:
            self.log("modo --sin-mqtt: no se conecta al broker")
        else:
            conectado = await self.puente.iniciar()
            if conectado:
                self.log("MQTT conectado a %s:%d" % (self.cfg.mqtt_host, self.cfg.mqtt_puerto))
            else:
                self.log("MQTT no disponible todavia; el backend sigue funcionando")

        if self.cfg.nube_activa:
            self.log("ThingSpeak activo (canal %s)" % self.cfg.ts_canal)
        else:
            self.log("ThingSpeak desactivado (sin claves): modo local")

        self.tareas = [
            asyncio.create_task(self._bucle_mensajes(), name="mensajes"),
            asyncio.create_task(self._bucle_talkback(), name="talkback"),
            asyncio.create_task(self._bucle_mantenimiento(), name="mantenimiento"),
        ]
        await self._iniciar_web()

    async def _iniciar_web(self) -> None:
        self._runner = web.AppRunner(self.app, access_log=None)
        await self._runner.setup()
        sitio = web.TCPSite(self._runner, self.cfg.host, self.cfg.puerto)
        await sitio.start()
        self.log("panel en http://%s:%d  (usuario %s)" % (
            self.cfg.host, self.cfg.puerto,
            "sin login" if self.cfg.sin_login else self.cfg.usuario))

    async def detener(self) -> None:
        for tarea in self.tareas:
            tarea.cancel()
        self.tareas = []
        self.comandos.cerrar()
        await self.puente.detener()
        await self.nube.cerrar()
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        await self.almacen.cerrar()
        self.log("backend detenido")

    async def esperar(self) -> None:
        await self._parar.wait()

    def solicitar_parada(self) -> None:
        self._parar.set()

    # -- mensajes MQTT -----------------------------------------------------
    async def _bucle_mensajes(self) -> None:
        while True:
            try:
                topico, datos = await self.puente.recibir()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.log("error leyendo del puente MQTT: %s" % exc)
                await asyncio.sleep(1)
                continue

            if topico is None:
                self.hub.publicar("estado", {"mqtt": False, "nodo": "desconectado"})
                continue

            try:
                await self._procesar(topico, datos)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.log("error procesando %s: %s" % (topico, exc))

    async def _procesar(self, topico: str, datos: dict) -> None:
        sufijo = topico.rsplit("/", 1)[-1]
        log_corto = self.log

        if sufijo == "telemetry":
            cuerpo = decodificar(datos["payload"])
            if not cuerpo:
                return
            await self.almacen.guardar_lectura(self.cfg.device_id, cuerpo)
            self.lecturas_guardadas += 1
            self.hub.publicar("lectura", _lectura_publica(cuerpo))
            await self._detectar_estado(cuerpo)
            await self.nube.subir(cuerpo)
            return

        if sufijo == "events":
            cuerpo = decodificar(datos["payload"])
            if not cuerpo:
                return
            await self.almacen.registrar_evento(
                self.cfg.device_id,
                kind=str(cuerpo.get("kind", "evento")),
                message=str(cuerpo.get("message", "")),
                severity=str(cuerpo.get("severity", "info")),
                state=cuerpo.get("state"),
                datos=cuerpo.get("data"),
            )
            self.eventos_guardados += 1
            self.hub.publicar("evento", cuerpo)
            if cuerpo.get("severity") == "critical":
                log_corto("EVENTO CRITICO: %s" % cuerpo.get("message", ""))
            return

        if sufijo == "status":
            texto = datos["payload"].decode("utf-8", "replace").strip()
            anterior = self.estado_nodo
            self.estado_nodo = texto
            self.hub.publicar("estado", {"nodo": texto, "mqtt": True})
            if texto != anterior:
                log_corto("nodo %s: %s" % (self.cfg.device_id, texto))
            return

        if sufijo == "ack":
            cuerpo = decodificar(datos["payload"])
            if cuerpo:
                confirmado = await self.comandos.confirmar(cuerpo)
                if not confirmado:
                    self.log("ACK sin comando pendiente: %s" % cuerpo.get("id"))
            return

    async def _detectar_estado(self, lectura: dict) -> None:
        estado = str(lectura.get("state") or "")
        if not estado or estado == self.ultimo_estado_seguridad:
            return
        await self.almacen.registrar_cambio_estado(
            self.cfg.device_id, self.ultimo_estado_seguridad, estado, "telemetria"
        )
        self.ultimo_estado_seguridad = estado
        self.hub.publicar("estado", {"seguridad": estado})

    # -- tareas de fondo ---------------------------------------------------
    async def _bucle_talkback(self) -> None:
        if not self.cfg.talkback_activo:
            return
        while True:
            await asyncio.sleep(self.cfg.ts_talkback_intervalo_s)
            try:
                comando = await self.nube.siguiente_comando()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.log("TalkBack con error: %s" % exc)
                continue
            if not comando:
                continue
            self.log("comando desde ThingSpeak: %s" % comando.get("cmd"))
            await self.comandos.ejecutar(comando.get("cmd"), comando.get("args"),
                                         source="thingspeak")

    async def _bucle_mantenimiento(self) -> None:
        ultima_purga = 0.0
        while True:
            await asyncio.sleep(5)
            try:
                expirados = await self.comandos.expirar()
                if expirados:
                    self.log("%d comando(s) marcados TIMEOUT" % expirados)
                ahora = time.time()
                if ahora - ultima_purga > 3600:
                    ultima_purga = ahora
                    borrado = await self.almacen.purgar(self.cfg.dias_retencion)
                    if any(borrado.values()):
                        self.log("purga de retencion: %s" % borrado)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                self.log("mantenimiento con error: %s" % exc)


def _lectura_publica(cuerpo: dict) -> dict:
    """Recorte de la telemetria para enviar al navegador."""
    claves = ("seq", "uptime_s", "temp_c", "hum_pct", "lux", "dist_cm", "motion",
              "state", "alarm", "siren", "locked", "alerts", "rssi", "sensor_errors")
    datos = {clave: cuerpo.get(clave) for clave in claves}
    datos["ts_utc"] = iso(ahora_utc())
    return datos


def cargar_seed(cfg: config_mod.Config) -> None:
    """Carga los datos de demostracion en la base (si existe el script)."""
    if not RUTA_SEED.exists():
        log("no se encontro sql/seed.sql; se omite --seed")
        return
    import sqlite3

    cfg.ruta_bd.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(str(cfg.ruta_bd))
    try:
        conexion.executescript((RAIZ / "sql" / "schema.sql").read_text(encoding="utf-8"))
        conexion.executescript(RUTA_SEED.read_text(encoding="utf-8"))
        conexion.commit()
        log("datos de demostracion cargados en %s" % cfg.ruta_bd)
    finally:
        conexion.close()


def construir_argumentos(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backend del sistema de seguridad Centinela IoT")
    parser.add_argument("--host", default=None, help="interfaz del panel")
    parser.add_argument("--puerto", type=int, default=None, help="puerto del panel")
    parser.add_argument("--sin-login", action="store_true",
                        help="panel abierto sin autenticacion (demostracion)")
    parser.add_argument("--seed", action="store_true",
                        help="cargar datos de demostracion antes de arrancar")
    parser.add_argument("--sin-mqtt", action="store_true",
                        help="no intentar conectar al broker (modo offline)")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser.parse_args(argv)


async def ejecutar(argv=None) -> int:
    args = construir_argumentos(argv)
    cfg = config_mod.cargar()
    if args.host:
        cfg = cfg.con(host=args.host)
    if args.puerto:
        cfg = cfg.con(puerto=args.puerto)
    if args.sin_login:
        cfg = cfg.con(sin_login=True)
    if args.seed:
        cargar_seed(cfg)

    backend = Backend(cfg, sin_mqtt=args.sin_mqtt)
    bucle = asyncio.get_running_loop()
    for senal in (signal.SIGINT, signal.SIGTERM):
        try:
            bucle.add_signal_handler(senal, backend.solicitar_parada)
        except (NotImplementedError, RuntimeError):
            pass

    await backend.arrancar()
    try:
        await backend.esperar()
    finally:
        await backend.detener()
    return 0


def main(argv=None) -> int:
    try:
        return asyncio.run(ejecutar(argv))
    except KeyboardInterrupt:
        log("interrumpido por el usuario")
        return 130


if __name__ == "__main__":
    sys.exit(main())
