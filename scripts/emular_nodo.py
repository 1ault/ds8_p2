"""Emulador del nodo ESP32 en CPython.

Reutiliza el codigo *real* del firmware (maquina de estados, controlador y
cliente MQTT) sustituyendo solo lo que depende del hardware: sensores,
actuadores y pantalla. Sirve para demostrar el sistema completo sin Wokwi y
para probar el backend de punta a punta.

Uso:
    python scripts/emular_nodo.py                      # contra HiveMQ publico
    python scripts/emular_nodo.py --escenario intruso
    python scripts/emular_nodo.py --host 127.0.0.1 --puerto 1883
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "firmware")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import config as fw  # noqa: E402  (configuracion del firmware)
import fsm  # noqa: E402
import mqtt_client  # noqa: E402
from app import Controlador  # noqa: E402


# ---------------------------------------------------------------------------
# Actuadores y pantalla emulados (sin GPIO)
# ---------------------------------------------------------------------------
class LedEmulado:
    def __init__(self, nombre):
        self.nombre = nombre
        self.encendido = False

    def encender(self):
        self.encendido = True

    def apagar(self):
        self.encendido = False

    def alternar(self):
        self.encendido = not self.encendido

    def fijar(self, valor):
        self.encendido = bool(valor)


class BuzzerEmulado:
    def __init__(self):
        self.activo = False
        self.frecuencia = 0

    def encender(self, frecuencia):
        self.activo = True
        self.frecuencia = frecuencia

    def apagar(self):
        self.activo = False


class CerraduraEmulada:
    def __init__(self):
        self.cerrada = True
        self.angulo = 0

    def abrir(self):
        self.cerrada = False
        self.angulo = 90

    def cerrar(self):
        self.cerrada = True
        self.angulo = 0


class PanelEmulado:
    def __init__(self):
        self.led_rojo = LedEmulado("rojo")
        self.led_verde = LedEmulado("verde")
        self.buzzer = BuzzerEmulado()
        self.cerradura = CerraduraEmulada()
        self.parpadeo = {"rojo": 0, "verde": 0}

    def estado(self):
        return {"led_rojo": self.led_rojo.encendido,
                "led_verde": self.led_verde.encendido,
                "sirena": self.buzzer.activo,
                "cerrada": self.cerradura.cerrada}

    def apagar_todo(self):
        self.led_rojo.apagar()
        self.led_verde.apagar()
        self.buzzer.apagar()


class PantallaEmulada:
    """Imita el OLED imprimiendo solo cuando algo relevante cambia."""

    def __init__(self, log=print):
        self._log = log
        self._ultimo = None

    def mostrar(self, datos):
        firma = (datos.get("state"), datos.get("siren"), datos.get("locked"),
                 datos.get("alerts"))
        if firma == self._ultimo:
            return True
        self._ultimo = firma
        self._log("[oled] %-9s temp=%s hum=%s luz=%s dist=%s mov=%s alertas=%s "
                  "cerrada=%s sirena=%s" % (
                      datos.get("state"), datos.get("temp_c"),
                      datos.get("hum_pct"), datos.get("lux"),
                      datos.get("dist_cm"), datos.get("movimiento", datos.get("motion")),
                      datos.get("alerts"), datos.get("locked"), datos.get("siren")))
        return True

    def aviso(self, texto):
        self._log("[oled] %s" % texto)
        return True

    def limpiar(self):
        return True


# ---------------------------------------------------------------------------
# Sensores simulados
# ---------------------------------------------------------------------------
class SensoresEmulados:
    """Genera lecturas plausibles y, en modo intruso, eventos de presencia."""

    def __init__(self, escenario="normal", intervalo=1.0, arranque=None):
        self.escenario = escenario
        self.intervalo = intervalo
        self.arranque = arranque or time.time()
        self.errores = 0
        self._ultimo = {"clima": -1e9, "movimiento": -1e9,
                        "distancia": -1e9, "luz": -1e9}
        self._valores = {"clima": {"temp_c": 24.0, "hum_pct": 55.0},
                         "luz": 40.0, "distancia": 180.0, "movimiento": False}
        self._movimiento_hasta = 0.0
        self._cercania_hasta = 0.0
        self._proximo_evento = time.time() + self._espera_evento()

    def _espera_evento(self):
        if self.escenario == "intruso":
            return random.uniform(8, 14)
        return random.uniform(45, 90)

    def _instante(self, ahora):
        return (ahora - self.arranque) % 86400.0

    def actualizar(self, ahora=None):
        ahora = ahora if ahora is not None else time.time()
        nuevas = {}
        instante = self._instante(ahora)

        if ahora - self._ultimo["clima"] >= fw.DHT_PERIOD_S:
            self._ultimo["clima"] = ahora
            ciclo = math.sin(instante / 86400.0 * 2 * math.pi)
            clima = {"temp_c": round(24.0 + 3.0 * ciclo + random.uniform(-.3, .3), 1),
                     "hum_pct": round(55.0 - 8.0 * ciclo + random.uniform(-1, 1), 1)}
            self._valores["clima"] = clima
            nuevas["clima"] = clima

        if ahora - self._ultimo["luz"] >= fw.LIGHT_PERIOD_S:
            self._ultimo["luz"] = ahora
            hora = (instante / 3600.0 + 6.0) % 24.0
            luz = max(0.0, 400.0 * math.sin((hora - 6) / 12.0 * math.pi))
            self._valores["luz"] = round(luz + random.uniform(0, 8), 1)
            nuevas["luz"] = self._valores["luz"]

        # Eventos de presencia (movimiento o acercamiento al sensor)
        if ahora >= self._proximo_evento:
            self._proximo_evento = ahora + self._espera_evento()
            if self.escenario == "intruso":
                self._movimiento_hasta = ahora + random.uniform(2, 4)
                self._cercania_hasta = self._movimiento_hasta
            else:
                self._movimiento_hasta = ahora + 1.5

        if ahora - self._ultimo["movimiento"] >= fw.PIR_PERIOD_S:
            self._ultimo["movimiento"] = ahora
            self._valores["movimiento"] = ahora < self._movimiento_hasta
            nuevas["movimiento"] = self._valores["movimiento"]

        if ahora - self._ultimo["distancia"] >= fw.DISTANCE_PERIOD_S:
            self._ultimo["distancia"] = ahora
            if ahora < self._cercania_hasta:
                distancia = random.uniform(25.0, 60.0)
            else:
                distancia = random.uniform(140.0, 300.0)
            self._valores["distancia"] = round(distancia, 1)
            nuevas["distancia"] = self._valores["distancia"]

        return nuevas

    def instantanea(self):
        return dict(self._valores)

    def total_errores(self):
        return self.errores


class WifiEmulada:
    def rssi(self):
        return random.randint(-62, -48)

    def estado(self):
        return {"conectado": True, "ssid": "Wokwi-GUEST", "ip": "10.13.37.2",
                "rssi": self.rssi(), "intentos": 1}


# ---------------------------------------------------------------------------
# Nodo completo
# ---------------------------------------------------------------------------
class NodoEmulado:
    """Une controlador real + hardware emulado + transporte (real o en memoria)."""

    def __init__(self, cliente=None, escenario="normal", salida_s=None,
                 log=print, cfg=fw, reloj=time.time):
        self.cfg = cfg
        self.log = log
        self.escenario = escenario
        self.sensores = SensoresEmulados(escenario)
        self.panel = PanelEmulado()
        self.pantalla = PantallaEmulada(log)
        self.maquina = fsm.crear_desde_config(cfg)
        if salida_s is not None:
            self.maquina.salida_s = salida_s
        self.cliente = cliente
        self.controlador = Controlador(cfg, WifiEmulada(), cliente, self.sensores,
                                       self.panel, self.pantalla, self.maquina,
                                       log=log, reloj=reloj, boton=False)

    def conectar_canal(self, cliente):
        """Permite inyectar otro transporte (por ejemplo, loopback)."""
        self.cliente = cliente
        self.controlador.cliente = cliente

    async def ejecutar(self):
        await self.controlador.ejecutar()


class ClienteLoopback:
    """Transporte en memoria: sustituye al broker en la demo sin Internet."""

    def __init__(self):
        self.conectado = True
        self.on_message = None
        self.hacia_backend = None

    async def conectar(self, will_topic=None, will_msg=None):
        self.conectado = True
        return True

    async def suscribir(self, topicos):
        return True

    async def publicar(self, topico, payload, qos=0, retain=False):
        if self.hacia_backend is not None:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            await self.hacia_backend(topico, {"payload": payload})
        return True

    async def esperar_caida(self):
        await asyncio.Event().wait()

    async def cerrar(self):
        self.conectado = False

    def entregar(self, topico, payload):
        """Simula un mensaje que llega desde el broker."""
        if self.on_message:
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            self.on_message(topico, payload, 1, False)


def construir_cliente(cfg=fw, host=None, puerto=None):
    return mqtt_client.MqttClient(
        host or cfg.MQTT_HOST,
        puerto or cfg.MQTT_PORT,
        cfg.MQTT_CLIENT_ID + "-emu",
        cfg.MQTT_KEEPALIVE_S,
        log=lambda mensaje: print("[mqtt] %s" % mensaje),
    )


async def ejecutar_standalone(args) -> int:
    log = lambda mensaje: print("[nodo] %s" % mensaje)  # noqa: E731
    cliente = construir_cliente(host=args.host, puerto=args.puerto)
    nodo = NodoEmulado(cliente=cliente, escenario=args.escenario,
                       salida_s=args.salida, log=log)
    log("emulador iniciado (escenario %s)" % args.escenario)
    try:
        await asyncio.wait_for(nodo.ejecutar(), args.duracion)
    except asyncio.TimeoutError:
        log("fin del tiempo solicitado")
    finally:
        await nodo.controlador.detener()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Emulador del nodo ESP32")
    parser.add_argument("--escenario", choices=["normal", "intruso"],
                        default="normal")
    parser.add_argument("--host", default=None, help="broker MQTT")
    parser.add_argument("--puerto", type=int, default=None)
    parser.add_argument("--salida", type=float, default=None,
                        help="segundos de cuenta regresiva al armar")
    parser.add_argument("--duracion", type=float, default=None,
                        help="detener tras N segundos")
    args = parser.parse_args(argv)
    try:
        return asyncio.run(ejecutar_standalone(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
