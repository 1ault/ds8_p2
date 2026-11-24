# Sensores del nodo: DHT22, PIR, HC-SR04 y LDR.
#
# Cada sensor sabe leer su magnitud y validar el resultado. La suite se encarga
# de respetar los periodos de muestreo, promediar (mediana) y no propagar
# errores: si un sensor falla, se conserva la ultima lectura valida y se cuenta
# el error. Asi una lectura mala nunca tumba el sistema de seguridad.
#
# UNIDADES Y FISICA QUE APARECE ABAJO
# -----------------------------------
# * **cm / us**: el HC-SR04 mide tiempo de vuelo del sonido. A 20 C el sonido
#   va a ~343 m/s = 0,0343 cm/us, o sea **29 us por cm de ida**. Como el pulso
#   va y vuelve, se dividen por **58** (29 x 2) para obtener centimetros.
# * **lux / ohm**: el LDR es una resistencia que baja con la luz. El modulo
#   arma un divisor con una resistencia fija de 10 kOhm; midiendo la tension
#   del punto medio se despeja la resistencia del LDR y de ahi los lux.
# * **ADC**: el conversor analogico-digital devuelve un entero (0..4095 en 12
#   bits) proporcional a la tension de entrada (0..3,3 V).

import time

import hal


def _mediana(valores):
    # Mediana de una lista: el valor del medio cuando se ordenan.
    #
    #     Se usa mediana y no promedio porque un solo disparo malo (un eco falsero)
    #     mueve el promedio pero casi no mueve la mediana. Con cantidad par se
    #     promedian los dos centrales; `n // 2` es la division entera (indice del
    #     medio).
    ordenados = sorted(valores)
    n = len(ordenados)
    if n == 0:
        return None
    medio = n // 2
    if n % 2:
        # Cantidad impar: hay un elemento justo en el medio.
        return ordenados[medio]
    return (ordenados[medio - 1] + ordenados[medio]) / 2.0


class DhtSensor:
    # Temperatura y humedad con reintentos y mediana de las ultimas muestras.

    def __init__(self, pin, retries=3, retry_delay_ms=60, ventana=3):
        self._dev = hal.DHT22(pin)
        self._retries = retries
        self._delay = retry_delay_ms
        self._ventana = ventana
        self._temps = []
        self._hums = []

    def leer(self):
        # Intenta hasta `retries` veces y devuelve la mediana de la ventana.
        #
        #         El DHT22 a veces contesta mal (ruido en el cable, timing); por eso se
        #         valida el rango y se reintenta. Si todos los intentos fallan se levanta
        #         `RuntimeError` y la suite cuenta el error sin cortar el programa.
        ultimo_error = None
        for intento in range(self._retries):
            try:
                temp, hum = self._dev.measure()
                if temp is None or hum is None:
                    raise ValueError("lectura vacia")
                # Rangos fisicamente posibles del DHT22 (-40..80 C, 0..100 %).
                if temp <= -100 or temp >= 100:
                    raise ValueError("temperatura fuera de rango")
                if hum < 0 or hum > 100:
                    raise ValueError("humedad fuera de rango")
                self._temps.append(float(temp))
                self._hums.append(float(hum))
                if len(self._temps) > self._ventana:
                    # Se descarta la muestra mas vieja (ventana corrediza).
                    self._temps.pop(0)
                    self._hums.pop(0)
                return {
                    "temp_c": round(_mediana(self._temps), 1),
                    "hum_pct": round(_mediana(self._hums), 1),
                }
            except Exception as exc:  # noqa: BLE001 - el sensor puede fallar
                ultimo_error = exc
                if intento < self._retries - 1 and self._delay:
                    # `sleep_ms` bloquea el bucle de eventos: por eso el delay
                    # es corto (60 ms) y solo entre reintentos.
                    time.sleep_ms(self._delay)
        raise RuntimeError("DHT22 sin lectura valida: %s" % ultimo_error)


class PirSensor:
    # Sensor de movimiento: salida digital con antirrebote por tiempo.
    #
    #     El HC-SR501 entrega 1 mientras detecta movimiento y lo mantiene un rato
    #     (se ajusta con el potenciometro del modulo, 5 s por defecto en Wokwi). Aca
    #     se agrega un tiempo de mantenimiento propio para que un pulso corto no se
    #     pierda entre dos muestreos.

    def __init__(self, pin, mantenimiento_ms=1500):
        self._pin = hal.entrada(pin)
        self._mantenimiento_ms = mantenimiento_ms
        self._ultimo_ms = None

    def leer(self):
        # True si hay movimiento ahora o lo hubo hace menos de 1,5 s.
        #
        #         `ticks_ms()` es un contador que puede dar la vuelta; por eso la resta
        #         se hace con `ticks_diff()` y nunca con `-`.
        ahora = time.ticks_ms()
        if self._pin.value():
            self._ultimo_ms = ahora
            return True
        if self._ultimo_ms is not None:
            if time.ticks_diff(ahora, self._ultimo_ms) < self._mantenimiento_ms:
                return True
        return False


class UltrasonicSensor:
    # HC-SR04: mide distancia en cm con mediana de tres disparos.
    #
    #     Protocolo: un pulso de 10 us en TRIG dispara la medicion y el sensor
    #     responde con un pulso en ECHO cuyo ancho es proporcional a la distancia
    #     (58 us por cm, ida y vuelta). Rango util: 2 a 400 cm.

    def __init__(self, pin_trig, pin_echo, min_cm=2.0, max_cm=400.0,
                 timeout_us=30000, muestras=3):
        self._trig = hal.salida(pin_trig)
        self._echo = hal.entrada(pin_echo)
        self._min = min_cm
        self._max = max_cm
        self._timeout = timeout_us
        self._muestras = muestras
        self._trig.off()

    def _disparo(self):
        # Un disparo: devuelve cm o None si no hubo eco valido.
        self._trig.off()
        time.sleep_us(5)
        self._trig.on()
        # 10 us en alto es el pulso que pide el datasheet para disparar.
        time.sleep_us(10)
        self._trig.off()
        ancho = hal.pulse_us(self._echo, 1, self._timeout)
        if ancho < 0:
            # -1/-2 = timeout: no hubo eco (nada enfrente o muy lejos).
            return None
        # 58 us por cm de ida y vuelta (ver docstring del modulo).
        distancia = ancho / 58.0
        if distancia < self._min or distancia > self._max:
            # Fuera de rango util: se descarta el disparo.
            return None
        return distancia

    def leer(self):
        # Mediana de tres disparos; error si ninguno fue valido.
        validas = []
        for _ in range(self._muestras):
            d = self._disparo()
            if d is not None:
                validas.append(d)
            time.sleep_ms(10)
        if not validas:
            raise RuntimeError("HC-SR04 sin eco valido")
        return round(_mediana(validas), 1)


class LightSensor:
    # LDR con salida analogica: convierte el ADC a lux.
    #
    #     Modelo del modulo (resistencia fija de 10 kOhm arriba, LDR a tierra):
    #         V = raw / max_raw * VCC                  tension en el punto medio
    #         R_LDR = serie * V / (VCC - V)            divisor de tension despejado
    #         lux = (RL10 * 10^gamma / R_LDR) ^ (1 / gamma)
    #
    #     Con mucha luz el LDR baja su resistencia, la tension de AO baja y el valor
    #     del ADC disminuye; en oscuridad el ADC sube y los lux tienden a cero.
    #
    #     Constantes del modelo (del datasheet tipico del LDR GL5528):
    #         RL10 = 50 kOhm a 10 lux   -> `rl10_kohm`
    #         gamma = 0.7               -> pendiente de la curva R vs lux

    def __init__(self, pin, vcc=3.3, rl10_kohm=50.0, gamma=0.7,
                 serie_ohm=10000.0):
        self._adc = hal.ADC(pin)
        self._vcc = vcc
        self._rl10 = rl10_kohm * 1000.0
        self._gamma = gamma
        self._serie = serie_ohm

    def leer(self):
        # Lee el ADC y devuelve lux (0..100000).
        max_raw = self._adc.max_raw()
        if not max_raw:
            max_raw = 4095
        raw = self._adc.read()
        if raw is None:
            raise RuntimeError("LDR sin lectura")
        # Regla de tres: valor del ADC -> tension en voltios.
        voltaje = float(raw) / float(max_raw) * self._vcc
        if voltaje <= 0.0:
            # 0 V = el LDR casi no tiene resistencia (luz muy fuerte).
            return self._tope()
        if voltaje >= self._vcc:
            # VCC = el divisor esta abierto (oscuridad total).
            return 0.0
        # Divisor: V = VCC * R_ldr / (serie + R_ldr) despejado para R_ldr.
        resistencia = self._serie * voltaje / (self._vcc - voltaje)
        if resistencia <= 0.0:
            return self._tope()
        # Curva del LDR: R = RL10 * (10 / lux) ^ gamma  despejado para lux.
        # `**` es potencia; `1.0 / self._gamma` invierte la exponencial.
        lux = (self._rl10 * (10.0 ** self._gamma) / resistencia) ** (1.0 / self._gamma)
        tope = self._tope()
        if lux > tope:
            lux = tope
        return round(lux, 1)

    def _tope(self):
        # Valor maximo que se informa (evita infinitos por division por 0).
        return 100000.0


class SensorSuite:
    # Agrupa los sensores y respeta sus periodos de muestreo.

    def __init__(self, sensores, reloj=None):
        # sensores: lista de tuplas (nombre, objeto_sensor, periodo_s)
        self._sensores = list(sensores)
        self._reloj = reloj or time.time
        self.lecturas = {}
        self.errores = {}
        self._ultimo = {}
        for nombre, _, _ in self._sensores:
            self.lecturas[nombre] = None
            self.errores[nombre] = 0
            # -1e9 = "hace muchisimo": la primera pasada lee todos.
            self._ultimo[nombre] = -1e9

    def nombres(self):
        return [n for n, _, _ in self._sensores]

    def actualizar(self, ahora=None):
        # Lee los sensores cuyo periodo vencio. Devuelve las lecturas nuevas.
        if ahora is None:
            ahora = self._reloj()
        nuevas = {}
        for nombre, sensor, periodo in self._sensores:
            espera = ahora - self._ultimo[nombre]
            if espera < 0:
                # El reloj monotono (ticks_ms) dio la vuelta: se trata como
                # periodo vencido para que la suite no se congele.
                espera = periodo
            if espera < periodo:
                continue
            self._ultimo[nombre] = ahora
            try:
                valor = sensor.leer()
            except Exception:  # noqa: BLE001
                # Se cuenta el error y se conserva la ultima lectura valida:
                # un sensor roto no puede tumbar el sistema de seguridad.
                self.errores[nombre] += 1
                continue
            self.lecturas[nombre] = valor
            nuevas[nombre] = valor
        return nuevas

    def instantanea(self):
        # Copia de la ultima lectura de cada sensor (para OLED y MQTT).
        return dict(self.lecturas)

    def total_errores(self):
        # Suma de errores de todos los sensores (va en la telemetria).
        total = 0
        for _, valor in self.errores.items():
            total += valor
        return total


def construir_desde_config(cfg):
    # Crea la suite con los sensores del proyecto.
    sensores = [
        ("clima", DhtSensor(cfg.PIN_DHT, retries=cfg.DHT_RETRIES,
                            retry_delay_ms=cfg.DHT_RETRY_DELAY_MS),
         cfg.DHT_PERIOD_S),
        ("movimiento", PirSensor(cfg.PIN_PIR), cfg.PIR_PERIOD_S),
        ("distancia", UltrasonicSensor(cfg.PIN_TRIG, cfg.PIN_ECHO,
                                       min_cm=2.0, max_cm=cfg.DIST_MAX_CM),
         cfg.DISTANCE_PERIOD_S),
        ("luz", LightSensor(cfg.PIN_LDR, vcc=cfg.ADC_VCC,
                            rl10_kohm=cfg.LDR_RL10_KOHM,
                            gamma=cfg.LDR_GAMMA,
                            serie_ohm=cfg.LDR_SERIE_OHM), cfg.LIGHT_PERIOD_S),
    ]
    return SensorSuite(sensores)
