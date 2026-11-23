"""Configuracion central del nodo ESP32 (Centinela IoT).

QUE ES ESTE ARCHIVO
-------------------
Es la **lista de ajustes** del nodo: a que pin va cada cosa, cada cuanto se
mide, a partir de que valor hay alarma, como se llama cada topico MQTT y con
que credenciales se conecta. Ningun otro archivo del firmware tiene numeros de
hardware ni de red escritos a mano: todos leen de aca.

Si manana cambias el buzzer del GPIO25 al GPIO32, tocas **una linea** de este
archivo (y el diagrama) y el resto del programa sigue igual. Eso es lo que se
llama "un unico punto de configuracion".

QUE ES ``const()``
------------------
`const(valor)` le dice a MicroPython "esto nunca cambia, reemplazalo por el
valor cuando compilas". El resultado es que no gasta RAM ni tiempo en buscar
el nombre cada vez que se usa. En la PC (CPython) el modulo `micropython` no
existe, asi que se usa la funcion de abajo, que simplemente devuelve el valor:
las pruebas corren igual.

Este archivo se ejecuta en la placa: solo constantes y cuentas simples, nada de
funciones ni bucles.
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
# `DEVICE_ID` viaja en cada topico MQTT: dos nodos con id distinto pueden
# convivir (uno en Wokwi y otro en la maqueta fisica, por ejemplo).
DEVICE_ID = const("dev01")
DEVICE_NAME = const("Centinela-Puerta-Principal")

# Red del simulador de Wokwi: no lleva contrasena y da salida a Internet.
# En la maqueta fisica esto se cambia por el WiFi real (ver README_VSCODE.md).
WIFI_SSID = const("Wokwi-GUEST")
WIFI_PASSWORD = const("")
WIFI_TIMEOUT_S = const(20)        # cuanto esperar la conexion antes de seguir

# Broker publico de HiveMQ (gratuito). Para HiveMQ Cloud usar el host y el
# puerto TLS 8883 que da el panel de la nube (MQTT_TLS = True en ese caso).
MQTT_HOST = const("broker.hivemq.com")
MQTT_PORT = const(1883)           # 1883 = MQTT sin cifrar; 8883 = con TLS
MQTT_TLS = const(False)
MQTT_USER = const("")
MQTT_PASSWORD = const("")
# Identificador de cliente MQTT: TIENE que ser unico en el broker. Con el
# publico broker.hivemq.com, dos nodos con el mismo id se expulsan entre si y
# el monitor serie repite "fallo de conexion MQTT" en bucle.
MQTT_CLIENT_ID = const("centinela-ault-dev01")
MQTT_KEEPALIVE_S = const(30)      # cada cuanto late la conexion
MQTT_RECONNECT_MIN_S = const(2)   # primera espera si se cae la conexion
MQTT_RECONNECT_MAX_S = const(60)  # tope del backoff (2, 4, 8, ... 60)

# ---------------------------------------------------------------------------
# Topicos: <prefijo>/<dispositivo>/<canal>
# ---------------------------------------------------------------------------
# Un topico es como una direccion: el nodo publica en `.../telemetry` y el
# backend esta suscripto a `centinela/+/#` (el `+` es un nivel cualquiera y el
# `#` todo lo que sigue). Los topicos se arman concatenando en tiempo de
# ejecucion: no pueden ir dentro de ``const()`` porque sumar cadenas no es una
# constante para MicroPython.
TOPIC_PREFIX = const("centinela")
TOPIC_TELEMETRY = TOPIC_PREFIX + "/" + DEVICE_ID + "/telemetry"   # lecturas
TOPIC_EVENTS = TOPIC_PREFIX + "/" + DEVICE_ID + "/events"         # eventos
TOPIC_STATUS = TOPIC_PREFIX + "/" + DEVICE_ID + "/status"         # online/offline
TOPIC_COMMAND = TOPIC_PREFIX + "/" + DEVICE_ID + "/cmd"           # ordenes al nodo
TOPIC_ACK = TOPIC_PREFIX + "/" + DEVICE_ID + "/ack"               # respuesta
TOPIC_CONFIG = TOPIC_PREFIX + "/" + DEVICE_ID + "/config"         # umbrales

# ---------------------------------------------------------------------------
# Mapa de pines (ESP32 DevKit C V4)
# ---------------------------------------------------------------------------
# Cada linea dice en que agujero del ESP32 esta conectado cada componente.
# Ojo con dos cosas del ESP32:
#   * GPIO34, 35, 36 y 39 son SOLO ENTRADA (no pueden manejar un LED).
#   * GPIO 6 a 11 estan ocupados por la memoria flash: no se usan nunca.
PIN_DHT = const(27)           # DHT22: un solo cable de datos
PIN_PIR = const(26)           # PIR HC-SR501: entrega 1 cuando hay movimiento
PIN_TRIG = const(5)           # HC-SR04: disparo (salida del ESP32)
PIN_ECHO = const(18)          # HC-SR04: eco (entrada al ESP32)
PIN_LDR = const(34)           # LDR: GPIO34 = ADC1, solo entrada
PIN_LED_RED = const(23)       # LED rojo: alarma
PIN_LED_GREEN = const(19)     # LED verde: armado
PIN_BUZZER = const(25)        # sirena (buzzer por PWM)
PIN_SERVO = const(13)         # servo de la cerradura
PIN_I2C_SDA = const(21)       # OLED: datos del bus I2C
PIN_I2C_SCL = const(22)       # OLED: reloj del bus I2C
PIN_BUTTON = const(4)         # pulsador de armar/desarmar (a GND)

# OLED SSD1306
I2C_FREQ_HZ = const(400000)   # 400 kHz: el refresco de pantalla tiene que ser rapido
OLED_WIDTH = const(128)       # pixeles de ancho
OLED_HEIGHT = const(64)       # pixeles de alto (8 renglones de 8 px)
OLED_ADDR = const(0x3C)       # direccion I2C del modulo (0x3C o 0x3D)

# ---------------------------------------------------------------------------
# Tiempos de muestreo (segundos)
# ---------------------------------------------------------------------------
# Cada sensor se lee a su ritmo: no tiene sentido consultar el DHT22 (que
# tarda ~2 s) cada 50 ms, ni el PIR una vez por minuto.
LOOP_TICK_S = const(0.05)       # cada cuanto se ejecuta el ciclo de seguridad
PIR_PERIOD_S = const(0.15)      # movimiento: rapido, es lo que dispara la alarma
DISTANCE_PERIOD_S = const(0.5)  # distancia: el ultrasonido es mas lento
DHT_PERIOD_S = const(5.0)       # clima: cambia despacio
LIGHT_PERIOD_S = const(1.0)     # luz: contexto, 1 s alcanza
TELEMETRY_PERIOD_S = const(5.0) # cada cuanto se publica por MQTT
OLED_PERIOD_S = const(0.6)      # cada cuanto se redibuja la pantalla
STATUS_PERIOD_S = const(30.0)   # latido de estado del nodo
BUTTON_DEBOUNCE_MS = const(250) # antirrebote: dos pulsaciones mas juntas se ignoran
# Sondeo del pulsador: 20 ms para no perder un clic corto (la tarea de
# sensores puede bloquear el bucle hasta 100 ms mientras mide el HC-SR04).
BUTTON_POLL_S = const(0.02)
# Cada cuantos segundos el nodo imprime un latido con su estado y el nivel del
# pulsador: es la forma de ver en el monitor serie que el bucle sigue vivo.
LATIDO_S = const(10.0)

# ---------------------------------------------------------------------------
# Umbrales de seguridad
# ---------------------------------------------------------------------------
EXIT_DELAY_S = const(10)          # tiempo para salir antes de armar
DIST_ALARM_CM = const(80.0)       # presencia mas cerca que esto = intrusion
DIST_MAX_CM = const(410.0)        # HC-SR04 mide 2-400 cm; 10 cm de margen
TEMP_ALARM_C = const(45.0)        # alerta de sobrecalentamiento
TEMP_MIN_VALID_C = const(-20.0)   # valores fuera de esto se consideran error
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
# `ADC_MAX_RAW` es el fondo de escala de 12 bits (2^12 - 1 = 4095). Los otros
# tres son del modelo del LDR: 50 kOhm a 10 lux, curva gamma 0,7 y la
# resistencia fija del divisor en el modulo (10 kOhm).
ADC_MAX_RAW = const(4095)
ADC_VCC = const(3.3)
LDR_RL10_KOHM = const(50.0)
LDR_GAMMA = const(0.7)
LDR_SERIE_OHM = const(10000.0)

# Servo de la cerradura (SG90)
# Los servos no se manejan por voltaje sino por el ANCHO del pulso: 500 us
# equivale a 0 grados, 2500 us a 180, y la repeticion es a 50 Hz (20 ms).
SERVO_FREQ_HZ = const(50)
SERVO_MIN_US = const(500)
SERVO_MAX_US = const(2500)
SERVO_LOCK_DEG = const(0)     # 0 grados = cerrada
SERVO_UNLOCK_DEG = const(90)  # 90 grados = abierta

# Sirena bitonal
# Dos tonos que se alternan cada 300 ms: eso es lo que suena a "wii-u wii-u".
# `BUZZER_DUTY` es el volumen: 512 sobre 1023 = 50 % del ciclo (mas duty, mas
# fuerte). Si el buzzer suena muy flojo se sube; si satura, se baja.
SIREN_FREQ_HIGH = const(2900)
SIREN_FREQ_LOW = const(2400)
SIREN_TOGGLE_MS = const(300)
BUZZER_DUTY = const(512)      # sobre 1023

# Version del contrato de datos publicada en cada mensaje
# `PROTOCOL_VERSION` avisa si cambia el formato JSON (para que el backend sepa
# leerlo); `FIRMWARE_VERSION` es la version del firmware y se ve en la primera
# linea del monitor serie al arrancar.
PROTOCOL_VERSION = const(1)
FIRMWARE_VERSION = const("2.0.4")
