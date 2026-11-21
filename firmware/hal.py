"""Capa de abstraccion de hardware (HAL) para MicroPython.

Todo el uso de `machine` queda concentrado aqui. El resto de los modulos
(llamados "drivers") reciben estos objetos por inyeccion, lo que permite
probarlos en CPython con dobles sin tocar hardware.

Se importa `machine` de forma diferida (dentro de las funciones) para que el
modulo pueda cargarse en un equipo de escritorio.
"""


def _machine():
    import machine

    return machine


class Pin:
    """Envoltorio delgado sobre `machine.Pin`.

    Los valores de `machine.Pin.IN` y `machine.Pin.OUT` son **propios de cada
    puerto**: en el ESP32 valen 1 y 2, y el 0 es ``GPIO_MODE_DISABLE``. Por eso
    aqui NUNCA se usan numeros fijos. Con ``IN = 0`` el ESP32 deshabilitaba la
    entrada y el PIR (GPIO26), el eco del HC-SR04 (GPIO18) y el pulsador
    (GPIO4) leian siempre 0: la alarma no disparaba y el boton no hacia nada.
    """

    def __init__(self, numero, modo, pull=None):
        self._numero = numero
        self._modo = modo
        self._pull = pull
        self._obj = None
        # Se crea de inmediato: si el pin no existe, el error aparece al
        # construir el componente y no en la primera lectura.
        self._instancia()

    def _instancia(self):
        if self._obj is None:
            m = _machine()
            kwargs = {}
            if self._pull is not None:
                kwargs["pull"] = self._pull
            self._obj = m.Pin(self._numero, self._modo, **kwargs)
        return self._obj

    def value(self, valor=None):
        pin = self._instancia()
        if valor is None:
            return pin.value()
        pin.value(valor)
        return valor

    def on(self):
        self.value(1)

    def off(self):
        self.value(0)


def pull_up():
    return _machine().Pin.PULL_UP


def pull_down():
    return _machine().Pin.PULL_DOWN


def entrada(numero, pull=None):
    """Entrada digital. `pull` es ``machine.Pin.PULL_UP``/``PULL_DOWN`` o None."""
    return Pin(numero, _machine().Pin.IN, pull=pull)


def salida(numero):
    """Salida digital (LEDs, servo, buzzer antes de crear el PWM)."""
    return Pin(numero, _machine().Pin.OUT)


class PWM:
    """PWM con compatibilidad entre versiones de MicroPython.

    ESP32 reciente expone `duty_u16`; versiones anteriores solo `duty`.
    """

    def __init__(self, pin_obj, freq=None, duty=None):
        self._pin = pin_obj
        self._obj = None
        if freq is not None:
            self.freq(freq)
        if duty is not None:
            self.duty(duty)

    def _instancia(self):
        if self._obj is None:
            self._obj = _machine().PWM(self._pin._instancia())
        return self._obj

    def freq(self, hz=None):
        obj = self._instancia()
        if hz is None:
            return obj.freq()
        obj.freq(int(hz))
        return hz

    def duty(self, valor=None):
        """Ciclo de trabajo en el rango 0-1023."""
        obj = self._instancia()
        if valor is None:
            return obj.duty()
        if hasattr(obj, "duty_u16"):
            obj.duty_u16(int(valor * 65535 / 1023))
        else:
            obj.duty(int(valor))
        return valor

    def duty_u16(self, valor=None):
        """Ciclo de trabajo en el rango 0-65535 (para servos)."""
        obj = self._instancia()
        if valor is None:
            return obj.duty_u16()
        if hasattr(obj, "duty_u16"):
            obj.duty_u16(int(valor))
        else:
            obj.duty(int(valor * 1023 / 65535))
        return valor

    def deinit(self):
        if self._obj is not None and hasattr(self._obj, "deinit"):
            self._obj.deinit()


class ADC:
    """ADC de una sola lectura con atenuacion para el rango 0-3.3 V."""

    def __init__(self, numero):
        self._numero = numero
        self._obj = None
        self._max = None

    def _instancia(self):
        if self._obj is None:
            m = _machine()
            self._obj = m.ADC(m.Pin(self._numero))
            if hasattr(self._obj, "atten"):
                self._obj.atten(m.ADC.ATTN_11DB)
            if hasattr(self._obj, "width"):
                self._obj.width(m.ADC.WIDTH_12BIT)
            if hasattr(self._obj, "read_u16"):
                self._max = 65535
            else:
                self._max = 4095
        return self._obj

    def max_raw(self):
        self._instancia()
        return self._max

    def read(self):
        obj = self._instancia()
        if hasattr(obj, "read_u16"):
            return obj.read_u16()
        return obj.read()


class I2C:
    def __init__(self, sda, scl, freq):
        self._sda = sda
        self._scl = scl
        self._freq = freq
        self._obj = None

    def _instancia(self):
        if self._obj is None:
            m = _machine()
            self._obj = m.I2C(0, sda=m.Pin(self._sda), scl=m.Pin(self._scl),
                              freq=self._freq)
        return self._obj

    def writeto(self, addr, datos):
        return self._instancia().writeto(addr, datos)

    def writevto(self, addr, vectores):
        obj = self._instancia()
        if hasattr(obj, "writevto"):
            return obj.writevto(addr, vectores)
        for v in vectores:
            obj.writeto(addr, v)

    def scan(self):
        obj = self._instancia()
        if hasattr(obj, "scan"):
            return obj.scan()
        return []


class DHT22:
    """Sensor DHT22 (temperatura y humedad)."""

    def __init__(self, numero):
        self._numero = numero
        self._obj = None

    def _instancia(self):
        if self._obj is None:
            import dht

            self._obj = dht.DHT22(_machine().Pin(self._numero))
        return self._obj

    def measure(self):
        self._instancia().measure()
        return self._instancia().temperature(), self._instancia().humidity()


def pulse_us(pin_obj, nivel, timeout_us):
    """Mide el ancho de un pulso en microsegundos (HC-SR04).

    Usa `machine.time_pulse_us` cuando esta disponible; si no, hace una espera
    activa equivalente.
    """
    m = _machine()
    if hasattr(m, "time_pulse_us"):
        return m.time_pulse_us(pin_obj._instancia(), nivel, timeout_us)
    import time

    obj = pin_obj._instancia()
    inicio = time.ticks_us()
    while obj.value() == nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -2
    while obj.value() != nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -1
    borde = time.ticks_us()
    while obj.value() == nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -2
    return time.ticks_diff(time.ticks_us(), borde)


class Reset:
    """Reinicio del microcontrolador (usado por el watchdog)."""

    @staticmethod
    def hard():
        _machine().reset()
