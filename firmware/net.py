"""Conexion WiFi con reintentos y consulta de estado.

`Wokwi-GUEST` es la red virtual del simulador: no lleva contrasena y ofrece
salida real a Internet, que es lo que permite llegar al broker MQTT.
"""

import asyncio
import time


def _network():
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
        if self._wlan is None:
            red = _network()
            self._wlan = red.WLAN(red.STA_IF)
        return self._wlan

    def conectado(self):
        try:
            return bool(self._interfaz().isconnected())
        except Exception:  # noqa: BLE001
            return False

    def ip(self):
        try:
            datos = self._interfaz().ifconfig()
            return datos[0]
        except Exception:  # noqa: BLE001
            return ""

    def rssi(self):
        wlan = self._interfaz()
        try:
            if hasattr(wlan, "status"):
                return wlan.status("rssi")
        except Exception:  # noqa: BLE001
            pass
        try:
            return wlan.config("rssi")
        except Exception:  # noqa: BLE001
            return None

    async def conectar(self, espera_max_s=None):
        """Activa la interfaz y espera la conexion. Devuelve True/False."""
        limite = espera_max_s if espera_max_s is not None else self.timeout_s
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
        return {
            "conectado": self.conectado(),
            "ssid": self.ssid,
            "ip": self.ip(),
            "rssi": self.rssi(),
            "intentos": self.intentos,
        }
