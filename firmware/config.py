"""Configuracion central del nodo ESP32 (Centinela IoT).

Un unico lugar para pines, umbrales, tiempos, topicos MQTT y credenciales.
Ningun otro modulo debe contener numeros magicos de hardware ni de red.

Este archivo se ejecuta en MicroPython: solo constantes y expresiones simples.
Las constantes se declaran con ``const()`` para que el parser las reemplace
por su valor en el bytecode (menos busquedas globales y menos RAM).
"""

# ``micropython`` es un modulo propio de la placa; en CPython no existe.
# El ``try`` permite correr las pruebas en la PC y el ``# type: ignore``
# silencia el aviso de VS Code (Pylance), que analiza con CPython.
try:
    from micropython import const  # type: ignore
except ImportError:
    def const(valor):
        return valor


# ---------------------------------------------------------------------------
# Identidad del dispositivo y red
# ---------------------------------------------------------------------------
DEVICE_ID = const("dev01")
DEVICE_NAME = const("Centinela-Puerta-Principal")

WIFI_SSID = const("Wokwi-GUEST")
WIFI_PASSWORD = const("")
WIFI_TIMEOUT_S = const(20)

# Broker publico de HiveMQ (gratuito). Para HiveMQ Cloud usar el host y el
# puerto TLS 8883 que da el panel de la nube.
MQTT_HOST = const("broker.hivemq.com")
MQTT_PORT = const(1883)
MQTT_TLS = const(False)
MQTT_USER = const("")
MQTT_PASSWORD = const("")
MQTT_CLIENT_ID = const("centinela-dev01")
MQTT_KEEPALIVE_S = const(30)
MQTT_RECONNECT_MIN_S = const(2)
MQTT_RECONNECT_MAX_S = const(60)

# ---------------------------------------------------------------------------
# Topicos: <prefijo>/<dispositivo>/<canal>
# ---------------------------------------------------------------------------
# Los topicos se arman concatenando en tiempo de ejecucion: no pueden ir
# dentro de ``const()`` porque la suma de cadenas no es una constante.
TOPIC_PREFIX = const("centinela")
TOPIC_TELEMETRY = TOPIC_PREFIX + "/" + DEVICE_ID + "/telemetry"
TOPIC_EVENTS = TOPIC_PREFIX + "/" + DEVICE_ID + "/events"
TOPIC_STATUS = TOPIC_PREFIX + "/" + DEVICE_ID + "/status"
TOPIC_COMMAND = TOPIC_PREFIX + "/" + DEVICE_ID + "/cmd"
TOPIC_ACK = TOPIC_PREFIX + "/" + DEVICE_ID + "/ack"
TOPIC_CONFIG = TOPIC_PREFIX + "/" + DEVICE_ID + "/config"

# ---------------------------------------------------------------------------
# Mapa de pines (ESP32 DevKit C V4)
# ---------------------------------------------------------------------------
PIN_DHT = const(27)
PIN_PIR = const(26)
PIN_TRIG = const(5)
PIN_ECHO = const(18)
PIN_LDR = const(34)          # GPIO34 = ADC1, solo entrada
PIN_LED_RED = const(23)
PIN_LED_GREEN = const(19)
PIN_BUZZER = const(25)
PIN_SERVO = const(13)
PIN_I2C_SDA = const(21)
PIN_I2C_SCL = const(22)
PIN_BUTTON = const(4)

I2C_FREQ_HZ = const(400000)
OLED_WIDTH = const(128)
OLED_HEIGHT = const(64)
OLED_ADDR = const(0x3C)

# ---------------------------------------------------------------------------
# Tiempos de muestreo (segundos)
# ---------------------------------------------------------------------------
LOOP_TICK_S = const(0.05)
PIR_PERIOD_S = const(0.15)
DISTANCE_PERIOD_S = const(0.5)
DHT_PERIOD_S = const(5.0)
LIGHT_PERIOD_S = const(1.0)
TELEMETRY_PERIOD_S = const(5.0)
OLED_PERIOD_S = const(0.6)
STATUS_PERIOD_S = const(30.0)
BUTTON_DEBOUNCE_MS = const(250)

# ---------------------------------------------------------------------------
# Umbrales de seguridad
# ---------------------------------------------------------------------------
EXIT_DELAY_S = const(10)          # tiempo para salir antes de armar
DIST_ALARM_CM = const(80.0)       # presencia mas cerca que esto = intrusion
DIST_MAX_CM = const(350.0)
TEMP_ALARM_C = const(45.0)        # alerta de sobrecalentamiento
TEMP_MIN_VALID_C = const(-20.0)
TEMP_MAX_VALID_C = const(80.0)
HUM_MIN_VALID = const(0.0)
HUM_MAX_VALID = const(100.0)
LUX_DARK = const(20.0)            # debajo de esto se considera oscuridad
SIREN_MAX_S = const(120)          # la sirena se calla sola a los 2 minutos
AUTO_RELOCK_S = const(8)          # la cerradura se cierra sola
UNLOCK_PIN = const("2468")        # PIN para abrir por comando remoto
PIN_INTENTOS_MAX = const(3)       # intentos fallidos antes de bloquear 30 s
PIN_BLOQUEO_S = const(30)

# Reintentos de lectura del DHT22 antes de descartar la muestra
DHT_RETRIES = const(3)
DHT_RETRY_DELAY_MS = const(60)

# ADC del LDR
ADC_MAX_RAW = const(4095)
ADC_VCC = const(3.3)
LDR_RL10_KOHM = const(50.0)
LDR_GAMMA = const(0.7)
LDR_SERIE_OHM = const(10000.0)

# Servo de la cerradura (SG90)
SERVO_FREQ_HZ = const(50)
SERVO_MIN_US = const(500)
SERVO_MAX_US = const(2500)
SERVO_LOCK_DEG = const(0)
SERVO_UNLOCK_DEG = const(90)

# Sirena bitonal
SIREN_FREQ_HIGH = const(2900)
SIREN_FREQ_LOW = const(2400)
SIREN_TOGGLE_MS = const(300)
BUZZER_DUTY = const(512)      # sobre 1023

# Version del contrato de datos publicada en cada mensaje
PROTOCOL_VERSION = const(1)
FIRMWARE_VERSION = const("2.0.0")
