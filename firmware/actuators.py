# Actuadores: LEDs, sirena (buzzer PWM) y cerradura (servo).
#
# QUE ES UN ACTUADOR
# ------------------
# Es lo contrario de un sensor: en vez de medir el mundo, **actua** sobre el.
# Aca hay cinco: dos LEDs, la sirena (buzzer), el servo de la cerradura y el
# OLED (que esta en `display.py`).
#
# REGLA IMPORTANTE DE ESTE ARCHIVO
# --------------------------------
# Todos los metodos son **sincronos y rapidos**: encienden, apagan o cambian una
# frecuencia y se van. Ninguno hace `sleep`. El parpadeo y el tono bitonal los
# resuelve el controlador desde sus tareas asincronas (mirando el reloj), porque
# si el actuador se quedara esperando, el resto del programa no correria: no se
# leerian los sensores, no se atenderia al pulsador ni al MQTT.

import hal


class Led:
    # LED simple con estado recordado (para no reescribir el GPIO).
    #
    #     Guardar `encendido` evita mandar el mismo valor al pin 20 veces por
    #     segundo: solo se escribe cuando cambia.

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
        # Enciende o apaga segun un booleano (comodo en las tareas).
        if valor:
            self.encender()
        else:
            self.apagar()

    def alternar(self):
        # Invierte el estado (asi se hace parpadear desde el bucle de LEDs).
        if self.encendido:
            self.apagar()
        else:
            self.encender()


class Buzzer:
    # Sirena piezoelectrico controlada por PWM.
    #
    #     Un buzzer pasivo no suena con "1" o "0": hay que hacerlo vibrar a una
    #     frecuencia. `frecuencia` define el **tono** (2400 Hz y 2900 Hz son los dos
    #     tonos de la sirena) y el ciclo de trabajo define el **volumen**.

    def __init__(self, pin, duty=512):
        self._pin = hal.salida(pin)
        # Se crea el PWM a 2400 Hz con 0 % (apagado) hasta que haga falta.
        self._pwm = hal.PWM(self._pin, freq=2400, duty=0)
        self._duty = duty
        self.activo = False

    def encender(self, frecuencia):
        # Hace sonar el buzzer a esa frecuencia (Hz).
        #
        #         Se pone `duty(0)` y recien despues el valor final: algunos canales
        #         PWM del ESP32 arrastran el estado anterior y ese "reset" evita un
        #         chasquido al cambiar de tono.
        self._pwm.freq(int(frecuencia))
        self._pwm.duty(0)
        self._pwm.duty(self._duty)
        self.activo = True

    def apagar(self):
        # Ciclo de trabajo en 0: el buzzer deja de vibrar.
        self._pwm.duty(0)
        self.activo = False

    def fijar(self, activo, frecuencia=2400):
        if activo:
            self.encender(frecuencia)
        else:
            self.apagar()

    def deinit(self):
        # Apaga y libera el canal PWM (al detener el programa).
        self.apagar()
        self._pwm.deinit()


class ServoLock:
    # Cerradura electrica con servo SG90.
    #
    #     0 grados = cerrada (pestillo fuera), 90 grados = abierta.
    #
    #     COMO SE CONTROLA UN SERVO
    #     -------------------------
    #     No se le manda un voltaje ni un "angulo": se le manda un pulso cada 20 ms
    #     (50 Hz) y el **ancho** de ese pulso es el angulo:
    #
    #         0,5 ms  -> 0 grados
    #         1,5 ms  -> 90 grados (mitad del recorrido)
    #         2,5 ms  -> 180 grados
    #
    #     Por eso la cuenta de `_duty_para` es: ancho del pulso en microsegundos ->
    #     fraccion del periodo de 20 ms -> valor de 16 bits (0..65535) que pide
    #     `duty_u16`.

    def __init__(self, pin, freq_hz=50, min_us=500, max_us=2500,
                 angulo_cerrado=0, angulo_abierto=90):
        self._pin = hal.salida(pin)
        self._pwm = hal.PWM(self._pin, freq=freq_hz, duty=0)
        self._min_us = min_us
        self._max_us = max_us
        # Periodo en microsegundos: 1.000.000 / 50 Hz = 20.000 us = 20 ms.
        self._periodo_us = 1000000.0 / float(freq_hz)
        self._cerrado = angulo_cerrado
        self._abierto = angulo_abierto
        self.angulo = None
        self.cerrada = None
        self.mover_a(angulo_cerrado)

    def _duty_para(self, angulo):
        # Convierte un angulo (0..180) al valor de `duty_u16` (0..65535).
        if angulo < 0:
            angulo = 0
        if angulo > 180:
            angulo = 180
        # Regla de tres: 0 grados -> min_us, 180 grados -> max_us.
        ancho = self._min_us + (self._max_us - self._min_us) * (angulo / 180.0)
        # Fraccion del periodo, escalada al rango 0..65535.
        return int(ancho / self._periodo_us * 65535)

    def mover_a(self, angulo):
        # Mueve el servo y recuerda si quedo cerrada (comparando con 0 grados).
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
    # Conjunto de actuadores del sistema, con nombres estables.

    def __init__(self, led_rojo, led_verde, buzzer, cerradura):
        self.led_rojo = led_rojo
        self.led_verde = led_verde
        self.buzzer = buzzer
        self.cerradura = cerradura
        # Patrones de parpadeo activos por LED (en Hz); 0 = fijo
        self.parpadeo = {"rojo": 0, "verde": 0}

    def estado(self):
        # Foto de como estan los actuadores (para el panel y las pruebas).
        return {
            "led_rojo": self.led_rojo.encendido,
            "led_verde": self.led_verde.encendido,
            "sirena": self.buzzer.activo,
            "cerrada": self.cerradura.cerrada,
            "angulo": self.cerradura.angulo,
        }

    def apagar_todo(self):
        # Deja el nodo en silencio y a oscuras (al detener o al arrancar).
        self.parpadeo["rojo"] = 0
        self.parpadeo["verde"] = 0
        self.led_rojo.apagar()
        self.led_verde.apagar()
        self.buzzer.apagar()


def construir_desde_config(cfg):
    # Arma el panel con los pines del proyecto.
    return PanelActuadores(
        led_rojo=Led(cfg.PIN_LED_RED, "rojo"),
        led_verde=Led(cfg.PIN_LED_GREEN, "verde"),
        buzzer=Buzzer(cfg.PIN_BUZZER, duty=cfg.BUZZER_DUTY),
        cerradura=ServoLock(cfg.PIN_SERVO, freq_hz=cfg.SERVO_FREQ_HZ,
                            min_us=cfg.SERVO_MIN_US, max_us=cfg.SERVO_MAX_US,
                            angulo_cerrado=cfg.SERVO_LOCK_DEG,
                            angulo_abierto=cfg.SERVO_UNLOCK_DEG),
    )
