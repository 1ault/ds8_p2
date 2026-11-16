"""Actuadores: LEDs, sirena (buzzer PWM) y cerradura (servo).

Todos los metodos son sincronos y baratos: el parpadeo y el tono bitonal se
resuelven desde las tareas asincronas del controlador, nunca con retardos
bloqueantes dentro del actuador.
"""

import hal


class Led:
    """LED simple con estado recordado (para no reescribir el GPIO)."""

    def __init__(self, pin, nombre="led"):
        self.nombre = nombre
        self._pin = hal.salida(pin)
        self.encendido = False
        self._pin.off()

    def encender(self):
        if not self.encendido:
            self._pin.on()
            self.encendido = True

    def apagar(self):
        if self.encendido:
            self._pin.off()
            self.encendido = False

    def fijar(self, valor):
        if valor:
            self.encender()
        else:
            self.apagar()

    def alternar(self):
        if self.encendido:
            self.apagar()
        else:
            self.encender()


class Buzzer:
    """Sirena piezoelectrico controlada por PWM."""

    def __init__(self, pin, duty=512):
        self._pin = hal.salida(pin)
        self._pwm = hal.PWM(self._pin, freq=2400, duty=0)
        self._duty = duty
        self.activo = False

    def encender(self, frecuencia):
        self._pwm.freq(int(frecuencia))
        self._pwm.duty(0)
        self._pwm.duty(self._duty)
        self.activo = True

    def apagar(self):
        self._pwm.duty(0)
        self.activo = False

    def fijar(self, activo, frecuencia=2400):
        if activo:
            self.encender(frecuencia)
        else:
            self.apagar()

    def deinit(self):
        self.apagar()
        self._pwm.deinit()


class ServoLock:
    """Cerradura electrica con servo SG90.

    0 grados = cerrada (pestillo fuera), 90 grados = abierta.
    """

    def __init__(self, pin, freq_hz=50, min_us=500, max_us=2500,
                 angulo_cerrado=0, angulo_abierto=90):
        self._pin = hal.salida(pin)
        self._pwm = hal.PWM(self._pin, freq=freq_hz, duty=0)
        self._min_us = min_us
        self._max_us = max_us
        self._periodo_us = 1000000.0 / float(freq_hz)
        self._cerrado = angulo_cerrado
        self._abierto = angulo_abierto
        self.angulo = None
        self.cerrada = None
        self.mover_a(angulo_cerrado)

    def _duty_para(self, angulo):
        if angulo < 0:
            angulo = 0
        if angulo > 180:
            angulo = 180
        ancho = self._min_us + (self._max_us - self._min_us) * (angulo / 180.0)
        return int(ancho / self._periodo_us * 65535)

    def mover_a(self, angulo):
        self._pwm.duty_u16(self._duty_para(angulo))
        self.angulo = angulo
        self.cerrada = angulo == self._cerrado
        return angulo

    def cerrar(self):
        return self.mover_a(self._cerrado)

    def abrir(self):
        return self.mover_a(self._abierto)

    def deinit(self):
        self._pwm.deinit()


class PanelActuadores:
    """Conjunto de actuadores del sistema, con nombres estables."""

    def __init__(self, led_rojo, led_verde, buzzer, cerradura):
        self.led_rojo = led_rojo
        self.led_verde = led_verde
        self.buzzer = buzzer
        self.cerradura = cerradura
        # Patrones de parpadeo activos por LED (en Hz); 0 = fijo
        self.parpadeo = {"rojo": 0, "verde": 0}

    def estado(self):
        return {
            "led_rojo": self.led_rojo.encendido,
            "led_verde": self.led_verde.encendido,
            "sirena": self.buzzer.activo,
            "cerrada": self.cerradura.cerrada,
            "angulo": self.cerradura.angulo,
        }

    def apagar_todo(self):
        self.parpadeo["rojo"] = 0
        self.parpadeo["verde"] = 0
        self.led_rojo.apagar()
        self.led_verde.apagar()
        self.buzzer.apagar()


def construir_desde_config(cfg):
    """Arma el panel con los pines del proyecto."""
    return PanelActuadores(
        led_rojo=Led(cfg.PIN_LED_RED, "rojo"),
        led_verde=Led(cfg.PIN_LED_GREEN, "verde"),
        buzzer=Buzzer(cfg.PIN_BUZZER, duty=cfg.BUZZER_DUTY),
        cerradura=ServoLock(cfg.PIN_SERVO, freq_hz=cfg.SERVO_FREQ_HZ,
                            min_us=cfg.SERVO_MIN_US, max_us=cfg.SERVO_MAX_US,
                            angulo_cerrado=cfg.SERVO_LOCK_DEG,
                            angulo_abierto=cfg.SERVO_UNLOCK_DEG),
    )
