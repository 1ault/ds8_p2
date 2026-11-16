"""Genera la guia paso a paso de instalacion y montaje (DOCX).

Uso:
    python scripts/build_guia_instalacion.py
Salida:
    docs/manuales/Guia_Instalacion_Montaje.docx
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in (str(RAIZ), str(RAIZ / "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

from _manual_estilo import GRIS, Manual  # noqa: E402

IMG = RAIZ / "docs" / "img"
CAP = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "docs" / "manuales" / "Guia_Instalacion_Montaje.docx"
VERSION = "2.0.0"


def construir() -> Path:
    manual = Manual(
        titulo="Guía de instalación y montaje",
        subtitulo="Cómo dejar el sistema funcionando desde cero: software, simulador, "
                  "hardware real y nube",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Guía de instalación y montaje",
    )

    manual.portada(
        imagen=IMG / "circuito.png",
        ancho_imagen_cm=15.2,
        resumen="Recorrido completo en diez pasos: requisitos, entorno de Python, "
                "configuración, base de datos, arranque del panel, nodo en Wokwi, montaje "
                "físico en protoboard, ThingSpeak y arranque automático.",
    )

    # ------------------------------------------------------------- contenido
    manual.h1("Contenido", nueva_pagina=False)
    manual.tabla(
        ["Paso", "Qué deja funcionando", "Tiempo"],
        [
            ["1", "el proyecto en el equipo", "2 min"],
            ["2", "Python y las dependencias", "5 min"],
            ["3", "la configuración (`.env`)", "3 min"],
            ["4", "la base de datos y sus datos de ejemplo", "1 min"],
            ["5", "el servidor y el panel en el navegador", "2 min"],
            ["6", "el nodo ESP32 en el simulador", "10 min"],
            ["7", "el montaje físico en protoboard (opcional)", "2 h"],
            ["8", "la nube de ThingSpeak (opcional)", "10 min"],
            ["9", "el arranque automático", "10 min"],
            ["10", "la verificación final", "5 min"],
        ],
        anchos=[1.4, 11.4, 3.8],
        alinear_centro=(0, 2),
        pie="Los diez pasos de la instalación.",
    )

    manual.nota("Hay **dos rutas**. La ruta del simulador (pasos 1 a 6) deja el sistema "
                "completo funcionando en unos 25 minutos y no necesita comprar nada. La ruta "
                "del hardware real añade el paso 7. Los pasos 8 y 9 son opcionales.", "nota")

    # ------------------------------------------------------------- 1. vision
    manual.h1("1. Qué se va a instalar")

    manual.parrafo("El sistema son tres piezas que se comunican por MQTT. En la ruta del "
                   "simulador, la pieza del nodo vive en el navegador y las otras dos en el "
                   "computador.")
    manual.figura(IMG / "arquitectura.png",
                  "Las tres piezas del sistema y cómo se comunican.", ancho_cm=15.4)
    manual.tabla(
        ["Pieza", "Dónde se instala", "Qué hay que hacer"],
        [
            ["Nodo (firmware)", "Wokwi (navegador) o ESP32 físico",
             "importar el proyecto o flashear MicroPython"],
            ["Servidor (backend + panel)", "el computador", "crear el entorno e instalar dependencias"],
            ["Nube (ThingSpeak)", "Internet", "opcional: crear el canal y pegar dos claves"],
        ],
        anchos=[4.2, 5.4, 7.0],
        pie="Dónde vive cada pieza.",
    )
    manual.parrafo("Al terminar la ruta del simulador tendrás: el panel abierto en el "
                   "navegador con lecturas en vivo, el histórico guardado en SQLite, los "
                   "comandos auditados y el nodo dibujado en Wokwi respondiendo al pulsador "
                   "y al sensor de movimiento.")

    # ---------------------------------------------------------- 2. requisitos
    manual.h1("2. Requisitos previos")

    manual.h2("2.1 Software")
    manual.tabla(
        ["Componente", "Versión mínima", "Para qué", "Cómo comprobarlo"],
        [
            ["Python", "3.10 (probado con 3.15)", "servidor, pruebas y herramientas",
             "`python --version`"],
            ["pip", "incluido con Python", "instalar dependencias", "`pip --version`"],
            ["Navegador", "Chrome, Edge o Firefox actual", "panel y simulador", "—"],
            ["Cuenta Wokwi", "gratuita", "simular el ESP32", "<https://wokwi.com>"],
            ["Cuenta ThingSpeak", "gratuita (opcional)", "nube y comandos remotos",
             "<https://thingspeak.com>"],
        ],
        anchos=[3.2, 4.2, 4.6, 4.6],
        pie="Requisitos de software.",
    )

    manual.h2("2.2 Materiales para el montaje físico (solo ruta B)")
    manual.tabla(
        ["Cantidad", "Componente", "Nota"],
        [
            ["1", "ESP32 DevKit C V4 (o similar de 30 pines)", "el cerebro del nodo"],
            ["1", "DHT22 (AM2302)", "temperatura y humedad"],
            ["1", "Sensor PIR HC-SR501", "movimiento por infrarrojos"],
            ["1", "HC-SR04", "distancia por ultrasonido"],
            ["1", "Módulo fotorresistor (LDR) con salida analógica", "luminosidad"],
            ["2", "LED (rojo y verde) + 2 resistencias de 220 Ω", "indicadores"],
            ["1", "Buzzer activo o pasivo", "sirena"],
            ["1", "Servo SG90", "cerradura simulada"],
            ["1", "Pantalla OLED SSD1306 128×64 I2C", "interfaz local"],
            ["1", "Pulsador de 4 patas", "armar y desarmar"],
            ["1", "Protoboard de 830 puntos", "base de montaje"],
            ["~30", "Cables jumper macho-macho y macho-hembra", "conexiones"],
            ["1", "Resistencia de 10 kΩ", "*pull-up* del DHT22"],
            ["2", "Resistencias de 1 kΩ y 2 kΩ", "divisor para el ECHO del HC-SR04"],
            ["1", "Fuente de 5 V / 2 A", "alimentar servo y sensor de distancia"],
        ],
        anchos=[2.0, 8.0, 6.6],
        alinear_centro=(0,),
        pie="Lista de materiales del montaje físico.",
    )
    manual.nota("El ESP32 entrega 3,3 V en sus pines lógicos y no es una fuente de "
                "alimentación: el servo y el HC-SR04 deben alimentarse aparte a 5 V, con el "
                "**GND en común** con el ESP32.", "aviso")

    # ------------------------------------------------------------- 3. obtener
    manual.h1("3. Paso 1 · Obtener el proyecto")

    manual.parrafo("Descomprime `Parcial2_IoT_Seguridad.zip` en una ruta local, por ejemplo "
                   "`C:\\Proyectos\\Centinela`. Evita carpetas sincronizadas como OneDrive: "
                   "el entorno virtual y la base de datos se comportan mal con la "
                   "sincronización en caliente.")
    manual.codigo("""Parcial2_IoT_Seguridad/
  backend/     servidor, API y panel (10 modulos)
  firmware/    12 modulos MicroPython + diagram.json + diagram_placa.json
  sql/         schema.sql, seed.sql, consultas.sql
  scripts/     demo, capturas, informes y empaquetado
  tests/       314 pruebas automatizadas
  docs/        documentacion, diagramas y capturas
  entregables/ documentos y paquetes finales
  requirements.txt  .env.example  README.md""")
    manual.parrafo("Comprueba que existen las carpetas `backend`, `firmware` y `sql`, y los "
                   "archivos `requirements.txt` y `.env.example`. Si usas Git:")
    manual.codigo("""git clone https://github.com/USUARIO/centinela-iot.git
cd centinela-iot""")

    # ------------------------------------------------------------- 4. python
    manual.h1("4. Paso 2 · Preparar Python")

    manual.h2("4.1 Crear el entorno e instalar")
    manual.parrafo("**Windows** (PowerShell o CMD), desde la carpeta del proyecto:")
    manual.codigo("""python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt""")
    manual.parrafo("**Linux o macOS**:")
    manual.codigo("""python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt""")
    manual.parrafo("Sabrás que el entorno está activo porque el aviso de la consola empieza "
                   "por `(.venv)`.")

    manual.h2("4.2 Verificar la instalación")
    manual.codigo("""python -c "import aiohttp, paho.mqtt, dotenv; print('dependencias ok')"
python --version
pip list""")
    manual.tabla(
        ["Paquete", "Versión esperada", "Para qué"],
        [
            ["`aiohttp`", "3.9 a 3.x", "servidor web, API REST y canal SSE"],
            ["`paho-mqtt`", "2.0 a 2.x", "cliente MQTT del servidor"],
            ["`python-dotenv`", "1.0 o superior", "leer el archivo `.env`"],
        ],
        anchos=[4.0, 4.6, 8.0],
        pie="Dependencias que instala el paso anterior.",
    )
    manual.parrafo("De forma opcional puedes instalar las de desarrollo (`pytest`, "
                   "`pytest-asyncio`, `Pillow`) y ejecutar las **314 pruebas** para "
                   "confirmar que todo está sano:")
    manual.codigo("""pip install -r requirements-dev.txt
python -m pytest""")

    # -------------------------------------------------------------- 5. .env
    manual.h1("5. Paso 3 · Configuración")

    manual.parrafo("El sistema funciona **sin configurar nada**: sin `.env` arranca en modo "
                   "local, con SQLite y el broker público. Pero conviene crear el archivo "
                   "para dejar fijos el usuario, la contraseña y la ruta de la base.")

    manual.h2("5.1 Crear el archivo")
    manual.codigo("""copy .env.example .env        :: Windows
cp .env.example .env          # Linux / macOS""")

    manual.h2("5.2 Qué tocar y qué dejar")
    manual.tabla(
        ["Variable", "Valor inicial", "Cuándo cambiarla"],
        [
            ["`WEB_PORT`", "`8000`", "si el puerto está ocupado (`8001`, `8010`…)"],
            ["`WEB_USER` / `WEB_PASSWORD`", "`admin` / `seguridad2026`", "siempre, si no es una demo"],
            ["`SECRET_KEY`", "texto de ejemplo", "siempre: firma la cookie de sesión"],
            ["`SIN_LOGIN`", "`0`", "poner `1` solo para demostraciones abiertas"],
            ["`DB_PATH`", "`data/centinela.db`", "para guardar la base en otro sitio"],
            ["`RETENTION_DAYS`", "`30`", "según cuánto histórico quieras conservar"],
            ["`MQTT_HOST` / `MQTT_PORT`", "`broker.hivemq.com` / `1883`", "si usas un broker propio"],
            ["`MQTT_TLS`", "`0`", "poner `1` con HiveMQ Cloud (puerto 8883)"],
            ["`TOPIC_PREFIX` / `DEVICE_ID`", "`centinela` / `dev01`", "si hay varios nodos"],
            ["`MQTT_ACK_TIMEOUT_S`", "`8`", "si la red es lenta"],
            ["`THINGSPEAK_*`", "vacías", "solo en el paso 8"],
        ],
        anchos=[4.8, 4.8, 7.0],
        pie="Variables del archivo .env.",
    )
    manual.parrafo("Un `.env` mínimo y seguro para empezar:")
    manual.codigo("""WEB_PORT=8000
WEB_USER=admin
WEB_PASSWORD=una-clave-propia
SECRET_KEY=una-cadena-larga-y-aleatoria
DB_PATH=data/centinela.db""")
    manual.nota("El archivo `.env` contiene credenciales y ya está en `.gitignore`: no se "
                "sube al repositorio. Si lo compartes, comparte `.env.example`.", "aviso")

    # --------------------------------------------------------------- 6. base
    manual.h1("6. Paso 4 · Base de datos")

    manual.parrafo("No hay que instalar ningún motor: SQLite viene con Python y el sistema "
                   "crea el archivo y el esquema la primera vez que arranca.")
    manual.vinetas([
        "El archivo se crea en `data\\centinela.db` (o en la ruta de `DB_PATH`).",
        "Al arrancar se aplica `sql/schema.sql`: 5 tablas, 7 índices y 5 vistas.",
        "La primera lectura o comando registra el dispositivo `dev01` en la tabla `devices`.",
    ])
    manual.parrafo("Si quieres histórico desde el primer minuto, carga los datos de ejemplo "
                   "(288 lecturas de 24 horas, eventos y comandos):")
    manual.codigo("""python -m backend.main --seed""")
    manual.parrafo("Comprueba el resultado desde otra consola:")
    manual.codigo("""python -m backend.cli resumen
python -m backend.cli estadisticas""")
    manual.tabla(
        ["Tabla", "Debe existir", "Filas con `--seed`"],
        [
            ["`devices`", "sí", "1"],
            ["`readings`", "sí", "288"],
            ["`events`", "sí", "7"],
            ["`commands`", "sí", "6"],
            ["`state_changes`", "sí", "3"],
        ],
        anchos=[4.4, 3.6, 8.6],
        alinear_centro=(1, 2),
        pie="Estado esperado de la base tras la siembra.",
    )

    # ------------------------------------------------------------- 7. arranque
    manual.h1("7. Paso 5 · Arrancar el servidor")

    manual.parrafo("Con el entorno activo y desde la carpeta del proyecto:")
    manual.codigo("""python -m backend.main --seed""")
    manual.parrafo("El registro debe mostrar, en este orden:")
    manual.codigo("""[backend] panel en http://127.0.0.1:8000
[backend] base de datos: data\\centinela.db
[backend] MQTT conectado a broker.hivemq.com:1883
[backend] suscrito a centinela/+/#""")
    manual.parrafo("Abre <http://127.0.0.1:8000>, entra con tu usuario y contraseña y "
                   "comprueba cuatro cosas: el estado `DESARMADO`, los sensores con valores, "
                   "la gráfica con las 288 lecturas y los eventos con hora.")
    manual.nota("Deja esta consola abierta: es el servidor. Para trabajar cómodo, abre una "
                "segunda consola para las consultas. La guía de prueba del monitoreo detalla "
                "las ocho comprobaciones de la interfaz.", "truco")

    manual.h2("7.1 Si el puerto está ocupado")
    manual.codigo("""python -m backend.main --seed --puerto 8001""")
    manual.parrafo("O averigua quién ocupa el 8000:")
    manual.codigo("""netstat -ano | findstr :8000
taskkill /PID <numero> /F""")

    # ---------------------------------------------------------------- 8. wokwi
    manual.h1("8. Paso 6 · El nodo en el simulador")

    manual.parrafo("Esta ruta deja el sistema completo sin comprar hardware: el ESP32 y sus "
                   "diez módulos se dibujan en el navegador y se conectan a Internet como un "
                   "dispositivo real.")

    manual.h2("8.1 Crear el proyecto")
    manual.numerada([
        "Entra a <https://wokwi.com> e inicia sesión (la cuenta gratuita sirve).",
        "Pulsa **New Project** y elige **ESP32 → MicroPython**.",
        "Abre el menú **⋯** y elige **Import / Export → Import project**.",
        "Selecciona `entregables/Wokwi_Centinela_IoT.zip`.",
    ])
    manual.parrafo("También se puede hacer a mano: crear los archivos con los mismos nombres "
                   "y pegar el contenido de cada uno de `firmware/`.")
    manual.tabla(
        ["Archivo", "Obligatorio", "Contenido"],
        [
            ["`main.py`", "sí", "es el que Wokwi ejecuta al pulsar Play"],
            ["`config.py`", "sí", "pines, umbrales, tiempos y tópicos"],
            ["`hal.py`, `bus.py`, `fsm.py`", "sí", "hardware, bus de eventos y máquina de estados"],
            ["`sensors.py`, `actuators.py`", "sí", "lectura de sensores y control de salidas"],
            ["`display.py`, `ssd1306.py`", "sí", "pantalla OLED"],
            ["`mqtt_client.py`, `net.py`", "sí", "cliente MQTT y WiFi"],
            ["`app.py`", "sí", "controlador con las tareas asíncronas"],
            ["`diagram.json`", "sí", "circuito de referencia"],
            ["`diagram_placa.json`", "opcional", "mismo circuito con placas de pan"],
        ],
        anchos=[5.4, 2.4, 8.8],
        alinear_centro=(1,),
        pie="Archivos que necesita el proyecto de Wokwi.",
    )

    manual.h2("8.2 Elegir el diagrama y arrancar")
    manual.parrafo("En la pestaña `diagram.json`, pega el contenido de `diagram.json` "
                   "(componentes sueltos) o el de `diagram_placa.json` (los mismos "
                   "componentes sobre dos placas de pan). Los dos son eléctricamente "
                   "idénticos.")
    manual.figura(CAP / "wokwi_01_circuito.png",
                  "El circuito en el simulador: placa, sensores, luces, sirena, cerradura y "
                  "pantalla.", ancho_cm=10.4)
    manual.parrafo("Pulsa **Play**. El monitor serie debe mostrar:")
    manual.codigo("""[centinela] arranque Centinela-Puerta-Principal (dev01) firmware 2.0.0
[centinela] pantalla OLED lista en 0x3C
[centinela] WiFi conectado: 10.13.37.2
[centinela] MQTT conectado a broker.hivemq.com:1883""")
    manual.nota("`Wokwi-GUEST` no lleva contraseña y da salida real a Internet: es lo que "
                "permite llegar al broker público. No hay que configurar nada en el nodo.", "truco")

    manual.h2("8.3 Comprobar que el nodo y el panel se hablan")
    manual.figura(CAP / "wokwi_03_oled_armado.png",
                  "La pantalla del nodo en estado ARMADO.", ancho_cm=8.2)
    manual.numerada([
        "Mira la pantalla del simulador: debe decir `CENTINELA  LISTO` y las lecturas.",
        "En el panel del navegador, la píldora debe pasar a `MQTT OK`.",
        "Pulsa el botón verde del circuito: el estado pasa a `ARMANDO` y el LED parpadea.",
        "Espera 10 segundos: queda `ARMADO` con el LED verde fijo.",
        "Haz clic en el sensor de movimiento y elige **Simulate motion**: suena la sirena y "
        "el estado pasa a `ALARMA`.",
    ])

    # ------------------------------------------------------------ 9. montaje
    manual.h1("9. Paso 7 · Montaje físico (opcional)")
    manual.parrafo("Si vas a montarlo en protoboard, este paso sustituye al simulador: el "
                   "mismo firmware corre en un ESP32 real y publica en el mismo broker.")

    manual.h2("9.1 Tabla de conexiones")
    manual.tabla(
        ["Componente", "Pin del componente", "Pin del ESP32", "Nota"],
        [
            ["DHT22", "`VCC`", "`3V3`", "—"],
            ["DHT22", "`DATA`", "`GPIO27`", "con *pull-up* de 10 kΩ a 3,3 V"],
            ["DHT22", "`GND`", "`GND`", "—"],
            ["PIR HC-SR501", "`VCC`", "`3V3`", "acepta 5 V, pero 3,3 V evita niveles altos"],
            ["PIR HC-SR501", "`OUT`", "`GPIO26`", "salida digital"],
            ["PIR HC-SR501", "`GND`", "`GND`", "—"],
            ["HC-SR04", "`VCC`", "`5 V` externos", "no alimentar de 3V3"],
            ["HC-SR04", "`TRIG`", "`GPIO5`", "—"],
            ["HC-SR04", "`ECHO`", "`GPIO18`", "**con divisor 1 kΩ / 2 kΩ**"],
            ["HC-SR04", "`GND`", "`GND` común", "—"],
            ["LDR (módulo)", "`AO`", "`GPIO34`", "solo entrada analógica"],
            ["LDR (módulo)", "`VCC` / `GND`", "`3V3` / `GND`", "—"],
            ["LED rojo", "ánodo → R 220 Ω", "`GPIO23`", "cátodo a `GND`"],
            ["LED verde", "ánodo → R 220 Ω", "`GPIO19`", "cátodo a `GND`"],
            ["Buzzer", "`+`", "`GPIO25`", "`-` a `GND`"],
            ["Servo SG90", "`PWM` (naranja)", "`GPIO13`", "—"],
            ["Servo SG90", "`V+` (rojo)", "`5 V` externos", "GND común con el ESP32"],
            ["OLED SSD1306", "`SDA` / `SCL`", "`GPIO21` / `GPIO22`", "I2C a 400 kHz"],
            ["OLED SSD1306", "`VCC` / `GND`", "`3V3` / `GND`", "dirección 0x3C"],
            ["Pulsador", "pata 1 / pata 2", "`GPIO4` / `GND`", "usa *pull-up* interno"],
        ],
        anchos=[3.2, 4.4, 4.4, 4.6],
        pie="Conexiones pin por pin. Coinciden con firmware/config.py y con diagram.json.",
    )

    manual.h2("9.2 Tres advertencias que cuestan un ESP32")
    manual.vinetas([
        "**El `ECHO` del HC-SR04 entrega 5 V y el ESP32 tolera 3,3 V.** Pon un divisor: "
        "`ECHO` → 1 kΩ → `GPIO18`, y desde `GPIO18` → 2 kΩ → `GND`. Sin él, el pin se daña.",
        "**El DHT22 necesita una resistencia de 10 kΩ** entre `DATA` y `VCC`; sin ella las "
        "lecturas fallan de forma intermitente.",
        "**Servo y sensor de distancia van a 5 V**, no al pin de 3,3 V del ESP32: la placa "
        "no puede entregar la corriente del servo y se reinicia. Une siempre los `GND`.",
    ])
    manual.nota("El `GPIO34` es **solo entrada**: sirve para el LDR y para nada más. Los "
                "`GPIO6` a `GPIO11` están reservados para la memoria flash y no se deben "
                "usar.", "aviso")

    manual.h2("9.3 Orden de montaje")
    manual.numerada([
        "Coloca el ESP32 en un extremo de la protoboard, con el puerto USB hacia fuera.",
        "Lleva las dos líneas de alimentación: una a `3V3` y otra a `GND`.",
        "Monta los LEDs con sus resistencias de 220 Ω en serie y conéctalos a `GPIO23` y `GPIO19`.",
        "Conecta el DHT22 con su resistencia de 10 kΩ, el PIR y el LDR a los GPIO indicados.",
        "Arma el divisor de 1 kΩ / 2 kΩ en la línea `ECHO` antes de conectarla al `GPIO18`.",
        "Conecta el OLED a `GPIO21` y `GPIO22`, y el pulsador entre `GPIO4` y `GND`.",
        "Lleva el servo y el HC-SR04 a la fuente de 5 V exterior, uniendo los `GND`.",
        "Revisa la tabla de conexiones dos veces antes de alimentar.",
    ])
    manual.figura(IMG / "circuito.png",
                  "Esquema completo del montaje físico.", ancho_cm=15.4)

    manual.h2("9.4 Cargar el firmware en la placa")
    manual.parrafo("El ESP32 debe tener **MicroPython** instalado. Con `mpremote` (incluido en "
                   "`pip install mpremote`) es directo:")
    manual.codigo("""pip install mpremote
mpremote connect auto fs cp firmware/config.py :config.py
mpremote connect auto fs cp firmware/main.py :main.py
mpremote connect auto reset""")
    manual.parrafo("Copia del mismo modo los otros nueve módulos (`hal.py`, `bus.py`, "
                   "`fsm.py`, `sensors.py`, `actuators.py`, `display.py`, `ssd1306.py`, "
                   "`mqtt_client.py`, `net.py`, `app.py`). Con **Thonny** también se puede: "
                   "abrir cada archivo y *Guardar en MicroPython*.")
    manual.parrafo("Después de reiniciar, en el monitor serie debe aparecer la misma "
                   "secuencia que en el simulador. Si el WiFi de casa tiene contraseña, "
                   "cámbiala en `config.py`:")
    manual.codigo("""WIFI_SSID = "MI-RED"
WIFI_PASSWORD = "mi-clave\"""")

    # --------------------------------------------------------------- 10. nube
    manual.h1("10. Paso 8 · ThingSpeak (opcional)")

    manual.parrafo("Sin este paso el sistema funciona igual: la nube es una copia de los "
                   "datos en Internet y una vía para enviar comandos a distancia.")

    manual.h2("10.1 Crear el canal")
    manual.numerada([
        "Entra a <https://thingspeak.com> y crea una cuenta gratuita.",
        "Ve a **Channels → New Channel** y escribe el nombre `Centinela IoT`.",
        "Marca los ocho campos con estos nombres y unidades.",
        "Guarda y copia el **Channel ID** y la **Write API Key**.",
    ])
    manual.tabla(
        ["Campo", "Nombre", "Unidad", "Qué guarda"],
        [
            ["field1", "Temperatura", "°C", "`temp_c`"],
            ["field2", "Humedad", "%", "`hum_pct`"],
            ["field3", "Luminosidad", "lux", "`lux`"],
            ["field4", "Distancia", "cm", "`dist_cm`"],
            ["field5", "Movimiento", "0/1", "`motion`"],
            ["field6", "Alarma", "0/1", "`alarm`"],
            ["field7", "Estado", "0–3", "0 desarmado, 1 armando, 2 armado, 3 alarma"],
            ["field8", "Alertas", "nº", "`alerts`"],
        ],
        anchos=[2.2, 4.4, 2.6, 7.4],
        pie="Los ocho campos del canal.",
    )

    manual.h2("10.2 Comandos desde la nube")
    manual.numerada([
        "En el canal, ve a **Apps → TalkBack → Add a TalkBack app**.",
        "Copia el **TalkBack ID** y su **API Key**.",
        "Pega las cuatro claves en el `.env`.",
        "Reinicia el backend y comprueba que el registro diga `ThingSpeak activo`.",
    ])
    manual.codigo("""THINGSPEAK_CHANNEL=1234567
THINGSPEAK_WRITE_KEY=XXXXXXXXXXXXXXXX
THINGSPEAK_TALKBACK_ID=9876
THINGSPEAK_TALKBACK_KEY=YYYYYYYYYYYY
THINGSPEAK_INTERVAL_S=20
TALKBACK_INTERVAL_S=15""")
    manual.parrafo("Para probar un comando, escribe `arm` en la cola de TalkBack. En unos "
                   "segundos el panel pasa a `ARMANDO` y en la tabla de comandos aparece una "
                   "fila con origen `thingspeak`.")
    manual.tabla(
        ["Texto en TalkBack", "Comando"],
        [
            ["`arm`", "arma el sistema"],
            ["`disarm`", "desarma"],
            ["`mute`", "silencia la sirena"],
            ["`unlock`", "abre la cerradura (con PIN configurado)"],
            ["`ping`", "responde con el uptime"],
        ],
        anchos=[5.0, 11.6],
        pie="Comandos aceptados en la cola de TalkBack.",
    )

    # ----------------------------------------------------- 11. arranque auto
    manual.h1("11. Paso 9 · Dejarlo funcionando solo")

    manual.h2("11.1 Windows · Programador de tareas")
    manual.parrafo("Crea una tarea que arranque el panel al iniciar sesión:")
    manual.codigo("""schtasks /Create /TN "Centinela IoT" /SC ONLOGON ^
  /TR "C:\\Proyectos\\Centinela\\.venv\\Scripts\\python.exe -m backend.main" ^
  /RL HIGHEST""")
    manual.parrafo("Se puede probar de inmediato con `schtasks /Run /TN \"Centinela IoT\"` y "
                   "borrar con `schtasks /Delete /TN \"Centinela IoT\" /F`. La carpeta de "
                   "trabajo debe ser la del proyecto, así que conviene un archivo `.bat`:")

    manual.h2("11.2 Linux · servicio systemd")
    manual.codigo("""[Unit]
Description=Centinela IoT backend
After=network-online.target

[Service]
WorkingDirectory=/opt/centinela
ExecStart=/opt/centinela/.venv/bin/python -m backend.main
Restart=always

[Install]
WantedBy=multi-user.target""")
    manual.parrafo("Guardar como `/etc/systemd/system/centinela.service` y activar:")
    manual.codigo("""sudo systemctl daemon-reload
sudo systemctl enable --now centinela
systemctl status centinela""")

    manual.h2("11.3 Registro y respaldo")
    manual.vinetas([
        "El registro sale por la consola; redirígelo a un archivo si corre como servicio "
        "(`>> centinela.log 2>&1`).",
        "Respalda `data/centinela.db` con una copia diaria; es todo el estado del sistema.",
        "La purga automática borra lo anterior a `RETENTION_DAYS` días, así que el archivo no "
        "crece sin control.",
        "Si publicas el panel fuera de la red local, ponlo detrás de un proxy con TLS y "
        "cambia `SECRET_KEY`, `WEB_PASSWORD` y el PIN.",
    ])

    # --------------------------------------------------------- 12. verificacion
    manual.h1("12. Paso 10 · Verificación final")

    manual.parrafo("Si las dieciséis comprobaciones pasan, el sistema está instalado y "
                   "funcionando.")
    manual.tabla(
        ["#", "Comprobación", "Dónde", "Esperado"],
        [
            ["1", "dependencias instaladas", "consola", "`import aiohttp, paho.mqtt` sin error"],
            ["2", "pruebas automatizadas", "consola", "314 aprobadas"],
            ["3", "base de datos creada", "`data/`", "existe `centinela.db`"],
            ["4", "servidor en marcha", "consola", "panel en `http://127.0.0.1:8000`"],
            ["5", "acceso al panel", "navegador", "entra con usuario y contraseña"],
            ["6", "broker conectado", "panel", "píldora `MQTT OK`"],
            ["7", "canal en vivo", "panel", "píldora `EN VIVO ON`"],
            ["8", "lecturas llegando", "panel", "los seis sensores con valores"],
            ["9", "histórico", "panel", "la gráfica dibuja y cambia con `1 H` / `24 H`"],
            ["10", "eventos", "panel", "hay al menos un evento con hora"],
            ["11", "nodo en el simulador", "Wokwi", "`MQTT conectado` en el monitor serie"],
            ["12", "armado", "panel o pulsador", "`ARMADO` tras 10 s"],
            ["13", "alarma", "Wokwi o panel", "sirena activa y evento crítico"],
            ["14", "cerradura", "panel", "abre 8 s con el PIN correcto"],
            ["15", "auditoría", "panel", "los comandos aparecen con estado y latencia"],
            ["16", "nube (si se configuró)", "ThingSpeak", "el canal recibe datos"],
        ],
        anchos=[0.9, 5.0, 4.0, 7.7],
        alinear_centro=(0,),
        pie="Lista de verificación de la instalación.",
    )
    manual.parrafo("Para las consultas y el detalle de cada pantalla, la guía de prueba del "
                   "monitoreo desarrolla las ocho comprobaciones de la interfaz.")

    # -------------------------------------------------------------- 13. fallas
    manual.h1("13. Problemas frecuentes")

    manual.tabla(
        ["Síntoma", "Causa", "Solución"],
        [
            ["`ModuleNotFoundError: aiohttp`", "no se activó el entorno virtual",
             "activar `.venv` y reinstalar"],
            ["`pip` falla al crear el venv", "ruta sincronizada o permisos del temporal",
             "crear el proyecto en una ruta local, sin OneDrive"],
            ["`OSError: [WinError 10048]`", "puerto ocupado", "`--puerto 8001`"],
            ["`database is locked`", "dos procesos con la misma base",
             "cerrar el otro backend"],
            ["`MQTT OFF` en el panel", "broker inalcanzable o firewall",
             "probar `--sin-mqtt`; revisar la salida a Internet"],
            ["Wokwi no muestra el circuito", "faltó `diagram.json`",
             "importar el ZIP completo"],
            ["El nodo no publica", "prefijo de tópicos distinto",
             "revisar `TOPIC_PREFIX` y `DEVICE_ID` en ambos lados"],
            ["El DHT22 falla intermitente", "falta la resistencia de 10 kΩ",
             "añadir el *pull-up*"],
            ["El ESP32 se reinicia al mover el servo", "el servo cuelga del pin de 3,3 V",
             "alimentarlo de la fuente de 5 V con GND común"],
            ["La distancia siempre da 0", "`ECHO` sin divisor o sin GND común",
             "revisar el divisor y la masa"],
            ["El OLED no enciende", "dirección I2C distinta o SDA/SCL cruzados",
             "probar `i2c.scan()`; suele ser 0x3C"],
            ["ThingSpeak no recibe", "claves vacías o canal sin campos",
             "revisar `.env`; debe decir `ThingSpeak activo`"],
        ],
        anchos=[4.6, 5.6, 6.4],
        pie="Fallas típicas de instalación y montaje.",
    )

    # ------------------------------------------------------------ 14. limpiar
    manual.h1("14. Cómo empezar de cero")

    manual.parrafo("Para repetir la instalación o entregar el equipo limpio:")
    manual.codigo("""deactivate                 :: salir del entorno virtual
rmdir /s /q .venv          :: borrar el entorno
del data\\centinela.db      :: borrar el histórico
del .env                   ;; borrar la configuracion""")
    manual.nota("Nunca borres `sql/`, `firmware/` ni `docs/`: son la fuente del sistema. Lo "
                "único regenerable es `.venv`, `data/` y `.env`.", "aviso")

    # ---------------------------------------------------------------- anexo
    manual.h1("Anexo · Todos los comandos")

    manual.h2("A.1 Instalación")
    manual.codigo("""python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest""")

    manual.h2("A.2 Arranque y prueba")
    manual.codigo("""copy .env.example .env
python -m backend.main --seed
python -m backend.main --seed --puerto 8001
python -m backend.main --sin-mqtt --sin-login
python scripts\\demo.py --reset --sembrar""")

    manual.h2("A.3 Consultas")
    manual.codigo("""python -m backend.cli resumen
python -m backend.cli historico --horas 6 --limite 20
python -m backend.cli eventos --severidad critical
python -m backend.cli comandos
python -m backend.cli estadisticas""")

    manual.h2("A.4 Firmware")
    manual.codigo("""pip install mpremote
mpremote connect auto fs cp firmware/main.py :main.py
mpremote connect auto fs ls
mpremote connect auto reset""")

    manual.h2("A.5 Documentos relacionados")
    manual.tabla(
        ["Documento", "Para qué sirve"],
        [
            ["`docs/instalacion.md`", "la versión resumida de esta guía"],
            ["`docs/guia_demo.md`", "guion de la demostración"],
            ["`docs/plataforma_nube.md`", "ThingSpeak y TalkBack con detalle"],
            ["`docs/manuales/Guia_Prueba_Monitoreo.docx`", "probar la interfaz y las consultas"],
            ["`docs/manuales/Manual_Tecnico_Centinela_IoT.docx`", "arquitectura y protocolo"],
            ["`docs/manuales/Manual_Usuario_Centinela_IoT.docx`", "uso del panel día a día"],
        ],
        anchos=[8.4, 8.2],
        pie="Dónde ampliar cada paso.",
    )

    manual.parrafo()
    manual.parrafo("— Fin de la guía de instalación —", alineacion="centro", cursiva=True,
                   color=GRIS)

    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
