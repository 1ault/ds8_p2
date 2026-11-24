# Conexion WiFi con reintentos y consulta de estado.
#
# QUE HACE
# --------
# Antes de hablar MQTT hay que estar en una red. Este modulo:
#
# 1. prende la interfaz WiFi en modo **estacion** (STA = "me conecto a un
#    router", a diferencia de AP = "soy yo el router"),
# 2. pide conectarse con SSID y contrasena,
# 3. espera sin bloquear hasta `timeout_s` (con `await asyncio.sleep`, que deja
#    correr las demas tareas mientras espera),
# 4. informa la IP y la **intensidad de senal** (RSSI).
#
# `Wokwi-GUEST` es la red virtual del simulador: no lleva contrasena y ofrece
# salida real a Internet, que es lo que permite llegar al broker MQTT.
#
# RSSI: se mide en dBm y siempre es negativo. -50 es "muy buena senal", -70
# "regular", -85 "al limite". Por eso en el OLED aparece `WiFi -54`.

import asyncio
import time


def _network():
    # Importa `network` recien cuando se usa (igual que hace `hal`).
    import network

    return network


class Wifi:
    def __init__(self, ssid, password="", timeout_s=20, log=None):
        self.ssid = ssid
        self.password = password
        self.timeout_s = timeout_s
        self._log = log or (lambda mensaje: None)
        self._wlan = None
        self.intentos = 0

    def _interfaz(self):
        # Crea (una sola vez) la interfaz WLAN en modo estacion.
        if self._wlan is None:
            red = _network()
            self._wlan = red.WLAN(red.STA_IF)
        return self._wlan

    def conectado(self):
        # True si la placa ya tiene IP. Nunca lanza error.
        try:
            return bool(self._interfaz().isconnected())
        except Exception:  # noqa: BLE001
            return False

    def ip(self):
        # IP asignada por el router, o "" si todavia no hay.
        try:
            datos = self._interfaz().ifconfig()
            # ifconfig() devuelve (ip, mascara, gateway, dns); la IP es [0].
            return datos[0]
        except Exception:  # noqa: BLE001
            return ""

    def rssi(self):
        # Intensidad de senal en dBm (negativo: mas cerca de 0 = mejor).
        wlan = self._interfaz()
        try:
            # MicroPython nuevo: status("rssi"); viejo: config("rssi").
            if hasattr(wlan, "status"):
                return wlan.status("rssi")
        except Exception:  # noqa: BLE001
            pass
        try:
            return wlan.config("rssi")
        except Exception:  # noqa: BLE001
            return None

    async def conectar(self, espera_max_s=None):
        # Activa la interfaz y espera la conexion. Devuelve True/False.
        #
        #         No usa `time.sleep` porque eso congelaria todo el programa durante 20
        #         segundos: usa `await asyncio.sleep(0.25)`, que devuelve el control al
        #         bucle entre intento e intento.
        limite = espera_max_s if espera_max_s is not None else self.timeout_s
        # El driver WiFi reserva varios KB seguidos: si el heap esta
        # fragmentado falla con "OSError: WiFi Out of Memory". Se recolecta
        # basura una vez y se reintenta antes de darse por vencido.
        try:
            wlan = self._interfaz()
        except OSError:
            import gc
            gc.collect()
            wlan = self._interfaz()
        self.intentos += 1
        try:
            if getattr(wlan, "active", None) is not None:
                wlan.active(True)
        except Exception:  # noqa: BLE001
            pass

        if self.conectado():
            return True

        try:
            wlan.connect(self.ssid, self.password)
        except Exception as exc:  # noqa: BLE001
            self._log("WiFi connect fallo: %s" % exc)
            return False

        inicio = time.time()
        while time.time() - inicio < limite:
            if self.conectado():
                self._log("WiFi conectado: %s" % self.ip())
                return True
            await asyncio.sleep(0.25)
        self._log("WiFi sin conexion tras %ds" % limite)
        return False

    def estado(self):
        # Resumen para el panel y la telemetria.
        return {
            "conectado": self.conectado(),
            "ssid": self.ssid,
            "ip": self.ip(),
            "rssi": self.rssi(),
            "intentos": self.intentos,
        }
