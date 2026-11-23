"""Capa de abstraccion de hardware (HAL) para MicroPython.

QUE ES UN HAL
-------------
Es la unica parte del firmware que habla con `machine`, `dht` y `network`.
Todo lo demas (FSM, controlador, sensores, actuadores) recibe estos objetos
por inyeccion. Dos motivos:

1. **Se puede probar en la PC**: `tests/support/fakes.py` reemplaza `machine`
   por dobles que recuerdan lo que se les pidio, y las 337 pruebas corren sin
   placa ni simulador.
2. **Un solo lugar para las rarezas del chip**: si cambia la version de
   MicroPython, se toca aca y no en diez archivos.

`machine` se importa **dentro** de las funciones (`_machine()`), no arriba,
para que este archivo se pueda cargar en CPython sin placa.

OJO CON LOS MODOS DE PIN
------------------------
Los valores de `machine.Pin.IN` y `machine.Pin.OUT` **son propios de cada
puerto**. En el ESP32 valen 1 y 2, y el 0 es ``GPIO_MODE_DISABLE``. Escribir
`IN = 0` (como hacia antes este archivo) deshabilitaba la entrada y el PIR, el
eco del HC-SR04 y el pulsador leian siempre 0. Por eso se usan SIEMPRE las
constantes del puerto.
"""


def _machine():
    """Importa `machine` recien cuando se necesita (ver docstring de arriba)."""
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
        """Crea (una sola vez) el `machine.Pin` real y lo devuelve."""
        if self._obj is None:
            m = _machine()
            kwargs = {}
            if self._pull is not None:
                kwargs["pull"] = self._pull
            self._obj = m.Pin(self._numero, self._modo, **kwargs)
        return self._obj

    def value(self, valor=None):
        """Lee el nivel (0/1) o lo escribe si se pasa `valor`."""
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
    """Constante del puerto para activar la resistencia de pull-up interna."""
    return _machine().Pin.PULL_UP


def pull_down():
    """Constante del puerto para activar la resistencia de pull-down interna."""
    return _machine().Pin.PULL_DOWN


def entrada(numero, pull=None):
    """Entrada digital. `pull` es ``machine.Pin.PULL_UP``/``PULL_DOWN`` o None."""
    return Pin(numero, _machine().Pin.IN, pull=pull)


def salida(numero):
    """Salida digital (LEDs, servo, buzzer antes de crear el PWM)."""
    return Pin(numero, _machine().Pin.OUT)


class PWM:
    """PWM con compatibilidad entre versiones de MicroPython.

    Un PWM es una salida que se prende y apaga miles de veces por segundo.
    Dos parametros la definen:

    * **frecuencia** (Hz): cuantas veces por segundo. Define el *tono* en un
      buzzer (2400 Hz suena distinto que 2900 Hz).
    * **ciclo de trabajo** (duty): que fraccion del tiempo esta en alto. 50 %
      es la mitad; con un buzzer, 50 % suena mas fuerte que 10 %.

    Hay dos escalas para el duty:

        `duty()`      0 .. 1023    (10 bits, la clasica de MicroPython)
        `duty_u16()`  0 .. 65535   (16 bits, la que usan los ESP32 nuevos)

    Por eso la conversion `valor * 65535 / 1023` (y al reves
    `valor * 1023 / 65535`): 1023 es el fondo de escala de una y 65535 de la
    otra. Es una regla de tres, no un numero magico.
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
        """Lee la frecuencia actual o la fija en Hz."""
        obj = self._instancia()
        if hz is None:
            return obj.freq()
        obj.freq(int(hz))
        return hz

    def duty(self, valor=None):
        """Ciclo de trabajo en el rango 0-1023.

        Si el objeto tiene `duty_u16` (ESP32 moderno) se convierte con la
        regla de tres; si no, se usa el `duty()` viejo tal cual.
        512 es el 50 %: `512 * 65535 / 1023 = 32799`.
        """
        obj = self._instancia()
        if valor is None:
            return obj.duty()
        if hasattr(obj, "duty_u16"):
            obj.duty_u16(int(valor * 65535 / 1023))
        else:
            obj.duty(int(valor))
        return valor

    def duty_u16(self, valor=None):
        """Ciclo de trabajo en el rango 0-65535 (lo usan los servos).

        El servo necesita una resolucion fina: a 50 Hz el pulso util va de
        0,5 ms a 2,5 ms sobre 20 ms de periodo, o sea del 2,5 % al 12,5 %,
        y en una escala de 1023 eso serian solo ~100 pasos.
        """
        obj = self._instancia()
        if valor is None:
            return obj.duty_u16()
        if hasattr(obj, "duty_u16"):
            obj.duty_u16(int(valor))
        else:
            obj.duty(int(valor * 1023 / 65535))
        return valor

    def deinit(self):
        """Libera el canal PWM (deja el pin como estaba)."""
        if self._obj is not None and hasattr(self._obj, "deinit"):
            self._obj.deinit()


class ADC:
    """ADC de una sola lectura con atenuacion para el rango 0-3.3 V.

    El ADC mide una tension y la convierte en un numero:

    * `WIDTH_12BIT` -> 12 bits -> valores de 0 a 4095.
    * `read_u16()` de los ESP32 nuevos -> 16 bits -> 0 a 65535.
    * `ATTN_11DB` amplia el rango de entrada hasta ~3,3 V (sin atenuar el
      maximo seria ~1,1 V y el LDR se saturaria enseguida).

    `max_raw()` informa ese fondo de escala para que `sensors.LightSensor`
    pueda convertir el numero a voltios sin adivinar.
    """

    def __init__(self, numero):
        self._numero = numero
        self._obj = None
        self._max = None

    def _instancia(self):
        if self._obj is None:
            m = _machine()
            self._obj = m.ADC(m.Pin(self._numero))
            # `hasattr` porque no todos los puertos tienen estas funciones.
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
        """Fondo de escala del ADC (4095 o 65535 segun el puerto)."""
        self._instancia()
        return self._max

    def read(self):
        """Lectura cruda del ADC (0 .. max_raw())."""
        obj = self._instancia()
        if hasattr(obj, "read_u16"):
            return obj.read_u16()
        return obj.read()


class I2C:
    """Bus I2C: dos cables (SDA y SCL) y una direccion por dispositivo.

    El OLED SSD1306 vive en la direccion 0x3C. Solo se usa el bus 0 y se
    inicializa a 400 kHz (fast mode) para que el refresco sea rapido.
    """

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
        """Escribe bytes en un dispositivo (asi se le mandan comandos al OLED)."""
        return self._instancia().writeto(addr, datos)

    def writevto(self, addr, vectores):
        """Escribe varios bloques seguidos (fallback si no hay `writevto`)."""
        obj = self._instancia()
        if hasattr(obj, "writevto"):
            return obj.writevto(addr, vectores)
        for v in vectores:
            obj.writeto(addr, v)

    def scan(self):
        """Lista las direcciones que responden (sirve para detectar el OLED)."""
        obj = self._instancia()
        if hasattr(obj, "scan"):
            return obj.scan()
        return []


class DHT22:
    """Sensor DHT22 (temperatura y humedad).

    Protocolo de un solo cable: `measure()` dispara la conversion (tarda ~2 s)
    y despues `temperature()`/`humidity()` devuelven el ultimo resultado. El
    driver `dht` configura el pin por su cuenta, por eso no se le pasa un
    `hal.Pin` sino un `machine.Pin`.
    """

    def __init__(self, numero):
        self._numero = numero
        self._obj = None

    def _instancia(self):
        if self._obj is None:
            import dht

            self._obj = dht.DHT22(_machine().Pin(self._numero))
        return self._obj

    def measure(self):
        """Dispara una medicion y devuelve (temperatura C, humedad %)."""
        self._instancia().measure()
        return self._instancia().temperature(), self._instancia().humidity()


def pulse_us(pin_obj, nivel, timeout_us):
    """Mide el ancho de un pulso en microsegundos (HC-SR04).

    El HC-SR04 devuelve el eco como un pulso alto en ECHO: dura ~58 us por
    cada centimetro de ida y vuelta. `machine.time_pulse_us` hace exactamente
    eso de forma nativa, pero si el puerto no la tiene se hace a mano.

    Los codigos de error son los del estandar:

        -1  se acabo el tiempo esperando que empiece el pulso
        -2  empezo el pulso pero no termino a tiempo

    `ticks_us()` puede dar la vuelta (es un contador de 32 bits), por eso la
    resta se hace con `ticks_diff()` y nunca con `-`.
    """
    m = _machine()
    if hasattr(m, "time_pulse_us"):
        return m.time_pulse_us(pin_obj._instancia(), nivel, timeout_us)
    import time

    obj = pin_obj._instancia()
    inicio = time.ticks_us()
    # 1) esperar a que el pin este en el nivel (arranque del pulso)
    while obj.value() == nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -2
    # 2) esperar el flanco contrario (fin del pulso)
    while obj.value() != nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -1
    borde = time.ticks_us()
    # 3) medir cuanto dura el pulso
    while obj.value() == nivel:
        if time.ticks_diff(time.ticks_us(), inicio) > timeout_us:
            return -2
    return time.ticks_diff(time.ticks_us(), borde)


class Reset:
    """Reinicio del microcontrolador (usado por el watchdog)."""

    @staticmethod
    def hard():
        _machine().reset()
