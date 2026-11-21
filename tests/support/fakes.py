"""Dobles de hardware para probar el firmware en CPython.

Nada de esto se ejecuta en el ESP32: son sustitutos de `machine`, `dht`,
`framebuf` y `network` que registran lo que el codigo hace, para poder
verificar la logica sin placas ni simulador.
"""

from __future__ import annotations

import time
import types


class DoblePin:
    """Pin digital falso.

    Los valores de IN/OUT/PULL_* son los del **ESP32** (IN=1, OUT=2,
    PULL_UP=2), no 0/1: asi una prueba detecta si el HAL vuelve a usar
    numeros fijos. En el ESP32, 0 es ``GPIO_MODE_DISABLE`` e inutiliza la
    entrada (fue el bug del PIR, del eco del HC-SR04 y del pulsador).
    """

    IN = 1
    OUT = 2
    PULL_UP = 2
    PULL_DOWN = 1

    instancias: list["DoblePin"] = []

    def __init__(self, numero, modo=None, pull=None):
        self.numero = numero
        self.modo = modo
        self.pull = pull
        self._valor = 0
        self.escrituras: list[int] = []
        self.lecturas = 0
        DoblePin.instancias.append(self)

    def value(self, valor=None):
        if valor is None:
            self.lecturas += 1
            return self._valor
        self._valor = 1 if valor else 0
        self.escrituras.append(self._valor)
        return self._valor

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)

    def simular(self, valor):
        """Cambia el valor leido (equivale a mover una entrada)."""
        self._valor = 1 if valor else 0
        return self


class DoblePWM:
    """PWM falso que recuerda frecuencia y ciclo de trabajo."""

    instancias: list["DoblePWM"] = []

    def __init__(self, pin):
        self.pin = pin
        self._freq = 0
        self._duty = 0
        self._duty_u16 = 0
        self.historial_freq: list[int] = []
        self.historial_duty: list[int] = []
        DoblePWM.instancias.append(self)

    def freq(self, valor=None):
        if valor is None:
            return self._freq
        self._freq = int(valor)
        self.historial_freq.append(self._freq)
        return self._freq

    def duty(self, valor=None):
        if valor is None:
            return self._duty
        self._duty = int(valor)
        self.historial_duty.append(self._duty)
        return self._duty

    def duty_u16(self, valor=None):
        if valor is None:
            return self._duty_u16
        self._duty_u16 = int(valor)
        return self._duty_u16

    def deinit(self):
        self.deinit_llamado = True


class DobleADC:
    """ADC falso: el valor se fija desde la prueba."""

    valor = 2000
    ATTN_11DB = 3
    WIDTH_12BIT = 12

    def __init__(self, pin):
        self.pin = pin
        self.atenuacion = None
        self.ancho = None

    def atten(self, valor):
        self.atenuacion = valor

    def width(self, valor):
        self.ancho = valor

    def read(self):
        return DobleADC.valor


class DobleI2C:
    """Bus I2C falso que acumula las escrituras por direccion."""

    fallo = False
    instancias: list["DobleI2C"] = []

    def __init__(self, canal, sda=None, scl=None, freq=None):
        self.canal = canal
        self.sda = sda
        self.scl = scl
        self.freq = freq
        self.escrituras: list[tuple[int, bytes]] = []
        DobleI2C.instancias.append(self)

    def writeto(self, direccion, datos):
        if DobleI2C.fallo:
            raise OSError("I2C sin respuesta")
        self.escrituras.append((direccion, bytes(datos)))
        return len(datos)

    def writevto(self, direccion, vectores):
        total = 0
        for vector in vectores:
            total += self.writeto(direccion, vector)
        return total

    def scan(self):
        return [0x3C]


class DobleDHT:
    """DHT22 falso con guion de lecturas programable."""

    lecturas: list = []
    indice = 0

    def __init__(self, pin):
        self.pin = pin
        self._temperatura = 25.0
        self._humedad = 50.0

    def measure(self):
        guion = DobleDHT.lecturas
        if not guion:
            return
        posicion = DobleDHT.indice % len(guion)
        DobleDHT.indice += 1
        item = guion[posicion]
        if isinstance(item, Exception):
            raise item
        if item is None:
            raise OSError("sin respuesta")
        self._temperatura, self._humedad = item

    def temperature(self):
        return self._temperatura

    def humidity(self):
        return self._humedad

    @classmethod
    def reiniciar(cls, lecturas=None):
        cls.lecturas = list(lecturas or [])
        cls.indice = 0


class DobleFrameBuffer:
    """Sustituto minimo de framebuf.FrameBuffer (MONO_VLSB)."""

    MONO_VLSB = 0
    MONO_HLSB = 3
    instancias: list["DobleFrameBuffer"] = []

    def __init__(self, buffer, ancho, alto, formato):
        self.buffer = buffer
        self.ancho = ancho
        self.alto = alto
        self.formato = formato
        self.pixeles = bytearray(ancho * alto)
        self.textos: list[tuple[str, int, int]] = []
        self.lineas = 0
        DobleFrameBuffer.instancias.append(self)

    def _poner(self, x, y, color):
        if 0 <= x < self.ancho and 0 <= y < self.alto:
            self.pixeles[y * self.ancho + x] = 1 if color else 0

    def fill(self, color):
        self.pixeles = bytearray([1 if color else 0]) * (self.ancho * self.alto)

    def pixel(self, x, y, color):
        self._poner(x, y, color)

    def text(self, texto, x, y, color=1):
        self.textos.append((texto, x, y))

    def line(self, x1, y1, x2, y2, color=1):
        self.lineas += 1

    def rect(self, x, y, ancho, alto, color=1):
        self.lineas += 1

    def fill_rect(self, x, y, ancho, alto, color=1):
        for ix in range(x, x + ancho):
            for iy in range(y, y + alto):
                self._poner(ix, iy, color)

    def hline(self, x, y, ancho, color=1):
        self.lineas += 1

    def vline(self, x, y, alto, color=1):
        self.lineas += 1

    def encendidos(self):
        return sum(self.pixeles)


class DobleWLAN:
    """Interfaz WiFi falsa."""

    conectada = True
    ssid = "Wokwi-GUEST"
    ip = "10.13.37.2"
    rssi = -54

    def __init__(self, interfaz):
        self.interfaz = interfaz
        self.activa = False
        self.conexiones = 0

    def active(self, valor=None):
        if valor is None:
            return self.activa
        self.activa = bool(valor)

    def connect(self, ssid, clave=None):
        if not DobleWLAN.conectada:
            raise OSError("sin red")
        self.ssid_usado = ssid
        self.conexiones += 1

    def isconnected(self):
        return bool(DobleWLAN.conectada)

    def ifconfig(self):
        return (DobleWLAN.ip, "255.255.255.0", "10.13.37.1", "8.8.8.8")

    def status(self, que=None):
        if que == "rssi":
            return DobleWLAN.rssi
        return 5 if self.isconnected() else 0

    def config(self, clave=None):
        if clave == "rssi":
            return DobleWLAN.rssi
        return None


# ---------------------------------------------------------------------------
# Instalacion de los modulos falsos
# ---------------------------------------------------------------------------
def instalar_maquina():
    maquina = types.ModuleType("machine")
    maquina.Pin = DoblePin
    maquina.PWM = DoblePWM
    maquina.ADC = DobleADC
    maquina.I2C = DobleI2C
    maquina.pulsos = {}
    maquina.reset_llamado = False

    def time_pulse_us(pin, nivel, timeout_us):
        if getattr(maquina, "pulso_excepcion", None) is not None:
            raise maquina.pulso_excepcion
        secuencia = getattr(maquina, "pulsos_secuencia", None)
        if secuencia:
            return secuencia.pop(0)
        return maquina.pulsos.get(pin.numero, 5800)

    def reset():
        maquina.reset_llamado = True

    maquina.time_pulse_us = time_pulse_us
    maquina.reset = reset

    import sys

    sys.modules["machine"] = maquina
    return maquina


def instalar_framebuf():
    modulo = types.ModuleType("framebuf")
    modulo.FrameBuffer = DobleFrameBuffer
    modulo.MONO_VLSB = 0
    modulo.MONO_HLSB = 3
    modulo.MONO_HMSB = 4
    modulo.RGB565 = 1
    import sys

    sys.modules["framebuf"] = modulo
    return modulo


def instalar_dht():
    modulo = types.ModuleType("dht")
    modulo.DHT22 = DobleDHT
    modulo.DHT11 = DobleDHT
    import sys

    sys.modules["dht"] = modulo
    return modulo


def instalar_network():
    modulo = types.ModuleType("network")
    modulo.STA_IF = 0
    modulo.AP_IF = 1
    modulo.WLAN = DobleWLAN
    import sys

    sys.modules["network"] = modulo
    return modulo


def instalar_tiempo():
    """Agrega a `time` las funciones de MicroPython que faltan en CPython."""
    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(time.monotonic() * 1000)
    if not hasattr(time, "ticks_us"):
        time.ticks_us = lambda: int(time.monotonic() * 1000000)
    if not hasattr(time, "ticks_diff"):
        time.ticks_diff = lambda a, b: a - b
    if not hasattr(time, "sleep_ms"):
        time.sleep_ms = lambda ms: None
    if not hasattr(time, "sleep_us"):
        time.sleep_us = lambda us: None
    return time


def limpiar_registros():
    """Reinicia los registros de los dobles entre pruebas."""
    import sys

    DoblePin.instancias = []
    DoblePWM.instancias = []
    DobleADC.valor = 2000
    DobleDHT.reiniciar()
    DobleWLAN.conectada = True
    DobleI2C.fallo = False

    maquina = sys.modules.get("machine")
    if maquina is not None:
        maquina.pulsos = {}
        maquina.pulsos_secuencia = []
        maquina.pulso_excepcion = None
        maquina.reset_llamado = False
