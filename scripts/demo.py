"""Demo completa del sistema en un solo comando.

Levanta el backend (MQTT + SQLite + panel) y un nodo emulado que ejecuta el
codigo real del firmware. Con `--sin-mqtt` el nodo y el backend se conectan en
memoria, de modo que la demostracion funciona sin Internet.

Uso:
    python scripts/demo.py --reset --sembrar --sin-login
    python scripts/demo.py --sin-mqtt --escenario intruso --duracion 60
    python scripts/demo.py --puerto 8010 --armar-auto 8
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "firmware")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from backend import config as config_mod  # noqa: E402
from backend.main import Backend, cargar_seed, log  # noqa: E402
from backend.web.app import SERVICIOS  # noqa: E402
from scripts.emular_nodo import (ClienteLoopback, NodoEmulado,  # noqa: E402
                                 construir_cliente)


class PuenteLoopback:
    """Puente MQTT falso que entrega los comandos directamente al nodo."""

    conectado = True

    def __init__(self):
        self.canal: ClienteLoopback | None = None
        self.enviados = 0

    async def iniciar(self):
        return True

    async def detener(self):
        return None

    def publicar(self, topico, payload, qos=1, retain=False):
        if self.canal is None:
            return False
        self.canal.entregar(topico, payload)
        self.enviados += 1
        return True

    async def recibir(self):
        await asyncio.Event().wait()

    def estado(self):
        return {"conectado": True, "host": "loopback", "puerto": 0,
                "tls": False, "recibidos": 0, "enviados": self.enviados,
                "error": None}


def limpiar_base(ruta: Path) -> None:
    for sufijo in ("", "-wal", "-shm"):
        archivo = Path(str(ruta) + sufijo)
        if archivo.exists():
            archivo.unlink()


def imprimir_resumen(backend: Backend, nodo: NodoEmulado) -> None:
    log("--- resumen de la demo ---")
    log("lecturas guardadas : %d" % backend.lecturas_guardadas)
    log("eventos guardados  : %d" % backend.eventos_guardados)
    log("comandos enviados  : %d" % backend.comandos.aceptados)
    log("estado del nodo    : %s" % nodo.maquina.estado)
    log("alertas del nodo   : %d" % nodo.maquina.alertas)
    log("cerradura          : %s" % ("cerrada" if nodo.panel.cerradura.cerrada
                                      else "abierta"))


async def esperar_nodo_conectado(backend: Backend, nodo: NodoEmulado,
                                 limite_s: float = 25.0) -> bool:
    """Espera a que el nodo este conectado y el backend lo haya visto online."""
    fin = time.time() + limite_s
    while time.time() < fin:
        if nodo.cliente.conectado and backend.estado_nodo == "online":
            return True
        await asyncio.sleep(0.2)
    return False


async def ejecutar(args) -> int:
    inicio = time.time()
    cfg = config_mod.cargar()
    if args.puerto:
        cfg = cfg.con(puerto=args.puerto)
    if args.sin_login:
        cfg = cfg.con(sin_login=True)

    if args.reset:
        limpiar_base(cfg.ruta_bd)
        log("base de datos reiniciada: %s" % cfg.ruta_bd)
    if args.sembrar or args.reset:
        cargar_seed(cfg)

    backend = Backend(cfg, sin_mqtt=args.sin_mqtt)

    canal = None
    if args.sin_mqtt:
        puente = PuenteLoopback()
        backend.puente = puente
        backend.comandos.puente = puente
        backend.app[SERVICIOS]["puente"] = puente
        canal = ClienteLoopback()

    await backend.arrancar()

    if args.sin_mqtt:
        canal.hacia_backend = backend._procesar
        puente.canal = canal
        cliente = canal
    else:
        cliente = construir_cliente(host=cfg.mqtt_host, puerto=cfg.mqtt_puerto)

    nodo = NodoEmulado(cliente=cliente, escenario=args.escenario,
                       salida_s=args.salida,
                       log=lambda mensaje: print("[nodo] %s" % mensaje))
    tarea_nodo = asyncio.create_task(nodo.ejecutar())

    log("panel listo en http://%s:%d  (%s)" % (
        cfg.host, cfg.puerto,
        "sin login" if cfg.sin_login else "usuario %s" % cfg.usuario))
    log("nodo emulado: escenario=%s  transporte=%s" % (
        args.escenario, "memoria" if args.sin_mqtt else "MQTT real"))

    if args.armar_auto:
        await asyncio.sleep(args.armar_auto)
        listo = await esperar_nodo_conectado(backend, nodo)
        if not listo:
            log("el nodo aun no aparece como 'online'; se envia el comando igual")
        log("armando el sistema automaticamente")
        resultado = await backend.comandos.ejecutar("arm", {}, source="demo")
        log("resultado del comando arm: ok=%s motivo=%s" % (
            resultado.get("ok"), resultado.get("motivo")))

    try:
        if args.duracion:
            restante = args.duracion - (time.time() - inicio)
            if restante > 0:
                await asyncio.sleep(restante)
        else:
            await backend.esperar()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        tarea_nodo.cancel()
        try:
            await nodo.controlador.detener()
        except Exception:  # noqa: BLE001
            pass
        imprimir_resumen(backend, nodo)
        await backend.detener()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Demo completa del sistema Centinela IoT")
    parser.add_argument("--puerto", type=int, default=8010)
    parser.add_argument("--sin-login", action="store_true", default=True,
                        help="panel abierto (por defecto en la demo)")
    parser.add_argument("--con-login", dest="sin_login", action="store_false")
    parser.add_argument("--sin-mqtt", action="store_true",
                        help="nodo y backend en memoria (sin broker)")
    parser.add_argument("--reset", action="store_true",
                        help="borra la base y siembra datos de ejemplo")
    parser.add_argument("--sembrar", action="store_true",
                        help="carga datos de demostracion sin borrar")
    parser.add_argument("--escenario", choices=["normal", "intruso"],
                        default="intruso")
    parser.add_argument("--salida", type=float, default=5.0,
                        help="cuenta regresiva de armado (segundos)")
    parser.add_argument("--armar-auto", type=float, default=None,
                        help="armar el sistema a los N segundos")
    parser.add_argument("--duracion", type=float, default=None,
                        help="detener la demo tras N segundos")
    args = parser.parse_args(argv)

    inicio = time.time()
    try:
        codigo = asyncio.run(ejecutar(args))
    except KeyboardInterrupt:
        codigo = 130
    log("duracion total: %.1f s" % (time.time() - inicio))
    return codigo


if __name__ == "__main__":
    sys.exit(main())
