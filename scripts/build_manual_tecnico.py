"""Genera el Manual Tecnico del sistema Centinela IoT (DOCX).

Uso:
    python scripts/build_manual_tecnico.py
Salida:
    docs/manuales/Manual_Tecnico_Centinela_IoT.docx
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
SALIDA = RAIZ / "docs" / "manuales" / "Manual_Tecnico_Centinela_IoT.docx"

VERSION = "2.0.0"


def construir() -> Path:
    manual = Manual(
        titulo="Manual técnico",
        subtitulo="Sistema IoT de seguridad con detección y alertas: arquitectura, "
                  "protocolo, servicios y operación",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Manual técnico",
    )

    manual.portada(
        imagen=IMG / "arquitectura.png",
        ancho_imagen_cm=15.2,
        resumen="Documento de referencia para instalar, operar y mantener el sistema "
                "Centinela IoT. Describe la arquitectura de cuatro capas, el protocolo "
                "MQTT, el diseño del firmware y del backend, el modelo de datos, la API "
                "del panel y los procedimientos de operación.",
    )

    # ------------------------------------------------------------------ indice
    manual.h1("Contenido", nueva_pagina=False)
    manual.parrafo("El documento sigue el recorrido de una implementación real: primero "
                   "el sistema completo, después cada capa y al final la puesta en marcha "
                   "y el mantenimiento.")
    manual.tabla(
        ["Sección", "Qué encontrarás"],
        [
            ["1. Introducción", "propósito, alcance, audiencia, convenciones y glosario"],
            ["2. Descripción general", "qué hace el sistema y cómo cubre el enunciado"],
            ["3. Arquitectura", "capas, componentes y decisiones de diseño"],
            ["4. Requisitos técnicos", "hardware, software, red y puertos"],
            ["5. Firmware del nodo", "módulos, HAL, máquina de estados, MQTT propio"],
            ["6. Protocolo MQTT", "tópicos, tramas, comandos y códigos de rechazo"],
            ["7. Backend de servicios", "concurrencia, persistencia, comandos y nube"],
            ["8. Base de datos", "tablas, vistas, índices y consultas de históricos"],
            ["9. Seguridad", "modelo de amenazas y controles implementados"],
            ["10. Instalación y despliegue", "entorno local, Wokwi, ThingSpeak producción"],
            ["11. Pruebas y calidad", "estrategia, resultados y limitaciones conocidas"],
            ["12. Operación y mantenimiento", "diagnóstico, respaldo, actualización"],
            ["13. Anexos", "estructura del repositorio, comandos y referencias"],
        ],
        anchos=[4.6, 12.0],
        fuente=9.0,
        pie="Mapa del documento.",
    )

    manual.nota("Los valores de configuración que aparecen en este manual corresponden a "
                "la versión **%s** del sistema. Cualquier cambio en `firmware/config.py` "
                "o en el archivo `.env` modifica el comportamiento descrito." % VERSION,
                "nota")

    manual.h2("Ficha del documento")
    manual.tabla(
        ["Indicador", "Valor"],
        [
            ["Módulos del firmware", "12 archivos Python para ESP32 / MicroPython"],
            ["Módulos del backend", "10 archivos Python sobre asyncio"],
            ["Tópicos MQTT", "6 (telemetría, eventos, estado, comando, ACK y configuración)"],
            ["Base de datos", "5 tablas, 5 vistas y 7 índices en SQLite"],
            ["Consultas de históricos", "12 documentadas en `sql/consultas.sql`"],
            ["Pruebas automatizadas", "314 casos con pytest"],
            ["Documentación", "este manual, el manual de usuario y 7 documentos técnicos"],
        ],
        anchos=[5.0, 11.6],
        pie="Cifras del sistema documentado.",
    )

    # ------------------------------------------------------------- 1. intro
    manual.h1("1. Introducción")

    manual.h2("1.1 Propósito")
    manual.parrafo("Este manual documenta el diseño, la implementación y la operación de "
                   "**Centinela IoT**, un sistema de seguridad residencial que detecta "
                   "intrusiones y emite alertas. Está dirigido a quien deba instalar el "
                   "sistema, mantenerlo o evaluar su funcionamiento técnico, y responde "
                   "a tres preguntas concretas: cómo está construido, por qué se tomó cada "
                   "decisión y qué hacer cuando algo no funciona.")

    manual.h2("1.2 Alcance")
    manual.parrafo("El documento cubre las cuatro capas del sistema:")
    manual.vinetas([
        "**Dispositivo**: firmware en MicroPython sobre ESP32 simulado en Wokwi.",
        "**Transporte**: broker MQTT (HiveMQ) con seis tópicos y QoS 0/1.",
        "**Servicios**: backend asíncrono en Python con SQLite, API REST, SSE y "
        "cliente de ThingSpeak.",
        "**Usuario**: panel web del operador y canal de ThingSpeak con TalkBack.",
    ])
    manual.parrafo("Queda fuera del alcance la integración con cerraduras físicas "
                   "certificadas, la gestión de múltiples viviendas y el aprovisionamiento "
                   "masivo de dispositivos; el apartado 11.4 recoge estas limitaciones.")

    manual.h2("1.3 Audiencia y convenciones")
    manual.tabla(
        ["Perfil", "Qué secciones leer primero"],
        [
            ["Docente evaluador", "3, 5, 6, 7, 11"],
            ["Desarrollador que retoma el código", "3, 5, 6, 7, 8, 13"],
            ["Administrador del sistema", "4, 10, 12"],
            ["Estudiante que expone la demo", "2, 10 y el manual de usuario"],
        ],
        anchos=[6.0, 10.6],
        pie="Lecturas recomendadas según el perfil.",
    )
    manual.parrafo("Convenciones tipográficas utilizadas:")
    manual.vinetas([
        "`texto en monoespaciado`: nombres de archivo, variables, comandos y valores.",
        "**Negrita**: conceptos clave y nombres de componentes.",
        "Los comandos de consola se muestran en bloques con fondo gris.",
        "Los valores entre comillas angulares, como `<enlace>`, son marcadores que se "
        "sustituyen por un valor real.",
    ])

    manual.h2("1.4 Glosario")
    manual.tabla(
        ["Término", "Definición"],
        [
            ["ACK", "Confirmación que envía el nodo al ejecutar un comando; cierra el ciclo "
                    "de auditoría y permite medir la latencia."],
            ["FSM", "Máquina de estados finita. En el firmware implementa los estados "
                    "DESARMADO, ARMANDO, ARMADO y ALARMA."],
            ["HAL", "Capa de abstracción de hardware: único punto del firmware que habla con "
                    "la librería `machine`."],
            ["HiveMQ", "Broker MQTT público usado como transporte entre nodo y backend."],
            ["LWT", "Last Will and Testament: mensaje que el broker publica si el nodo "
                    "desaparece sin desconectarse limpiamente."],
            ["QoS", "Calidad de servicio MQTT: 0 (sin confirmación) o 1 (con confirmación)."],
            ["SSE", "Server-Sent Events: canal unidireccional servidor → navegador usado por "
                    "el panel para actualizarse en vivo."],
            ["TalkBack", "Aplicación de ThingSpeak que encola comandos para que el backend "
                         "los envíe al dispositivo."],
            ["Umbral", "Valor que separa lo normal de lo anómalo (por ejemplo, 80 cm de "
                       "distancia o 45 °C de temperatura)."],
        ],
        anchos=[3.6, 13.0],
        pie="Glosario de términos técnicos usados en el documento.",
    )

    # -------------------------------------------------- 2. descripcion general
    manual.h1("2. Descripción general")

    manual.h2("2.1 Qué hace el sistema")
    manual.parrafo("Centinela IoT vigila una puerta de acceso. El nodo lee cuatro sensores "
                   "y, según el estado de seguridad, decide si debe encender la sirena, "
                   "cerrar la cerradura o avisar al operador. Todo lo que ocurre se guarda "
                   "con marca de tiempo en una base de datos y se puede consultar en un "
                   "panel web en tiempo real, desde la red local o desde la nube.")
    manual.tabla(
        ["Función", "Dónde se implementa"],
        [
            ["Lectura de 4 sensores (temperatura, humedad, movimiento, luz y distancia)",
             "`firmware/sensors.py`"],
            ["Control de 5 actuadores (2 LEDs, sirena, servo-cerradura, OLED)",
             "`firmware/actuators.py`, `display.py`"],
            ["Máquina de estados de seguridad", "`firmware/fsm.py`"],
            ["Cliente MQTT con QoS 0/1 y Last Will", "`firmware/mqtt_client.py`"],
            ["Histórico con marca de tiempo en SQLite", "`backend/storage.py`"],
            ["Auditoría de comandos con ACK y latencia", "`backend/commands.py`"],
            ["Consultas de históricos (12 SQL + CLI + API)", "`sql/consultas.sql`, `backend/cli.py`"],
            ["Carga en ThingSpeak y comandos por TalkBack", "`backend/cloud.py`"],
            ["Panel en tiempo real con login y control", "`backend/web/`"],
            ["Programación modular orientada a eventos", "`firmware/bus.py`, `backend/bus.py`"],
        ],
        anchos=[10.4, 6.2],
        pie="Funciones del sistema y su ubicación en el código.",
    )

    manual.h2("2.2 Cómo se cubre el enunciado")
    manual.parrafo("El enunciado del parcial pide un mínimo de dos sensores y dos "
                   "actuadores, código Python modular, manejo de GPIO con librerías "
                   "apropiadas, cliente MQTT en el dispositivo, base de datos con "
                   "histórico, plataforma en la nube, panel en tiempo real y recepción de "
                   "comandos desde la nube. La tabla siguiente resume el cumplimiento:")
    manual.tabla(
        ["Requisito", "Solución implementada", "Cumple"],
        [
            ["≥ 2 sensores", "DHT22, PIR, HC-SR04 y LDR (cuatro)", "4"],
            ["≥ 2 actuadores", "LED rojo, LED verde, sirena PWM, servo-cerradura y OLED", "5"],
            ["Python modular", "12 módulos de firmware y 10 de backend, con docstrings", "Sí"],
            ["GPIO con librerías apropiadas", "`machine` (Pin, PWM, ADC, I2C) aislado en `hal.py`", "Sí"],
            ["Cliente MQTT en el dispositivo", "MQTT 3.1.1 propio sobre asyncio, QoS 0/1, LWT", "Sí"],
            ["Base de datos con histórico", "SQLite con 5 tablas, 5 vistas y marcas de tiempo", "Sí"],
            ["Consultas de históricos", "12 consultas documentadas, CLI y API REST", "Sí"],
            ["Plataforma en la nube", "ThingSpeak: canal de 8 campos", "Sí"],
            ["Panel en tiempo real", "aiohttp con SSE y gráfica en canvas", "Sí"],
            ["Comandos desde la nube", "TalkBack → MQTT → nodo → ACK", "Sí"],
        ],
        anchos=[5.0, 9.4, 2.2],
        alinear_centro=(2,),
        pie="Correspondencia entre el enunciado y la implementación.",
    )

    # -------------------------------------------------------- 3. arquitectura
    manual.h1("3. Arquitectura")

    manual.h2("3.1 Vista de capas")
    manual.parrafo("El sistema se organiza en cuatro capas con responsabilidades "
                   "separadas. Cada capa se puede sustituir sin reescribir las demás: el "
                   "firmware no sabe qué base de datos se usa y el panel no sabe cómo está "
                   "cableado el ESP32.")
    manual.figura(IMG / "arquitectura.png",
                  "Arquitectura de cuatro capas: dispositivo, broker MQTT, backend asíncrono "
                  "y usuario/nube.", ancho_cm=16.0)

    manual.h2("3.2 Componentes y responsabilidades")
    manual.tabla(
        ["Capa", "Componente", "Responsabilidad"],
        [
            ["Dispositivo", "ESP32 + MicroPython", "adquisición, decisión local y control de "
                                                  "actuadores sin depender de la red"],
            ["Dispositivo", "cliente MQTT propio", "publicar telemetría y eventos, recibir "
                                                  "comandos y confirmarlos"],
            ["Transporte", "broker HiveMQ", "reparto de mensajes, QoS y detección de caída "
                                           "mediante LWT"],
            ["Servicios", "puente MQTT", "traducir paho-mqtt (hilos) al bucle asíncrono"],
            ["Servicios", "almacén SQLite", "histórico, eventos, comandos y transiciones"],
            ["Servicios", "servicio de comandos", "validar, auditar, enviar y esperar ACK"],
            ["Servicios", "cliente ThingSpeak", "subir lecturas y recoger comandos de TalkBack"],
            ["Servicios", "API REST + SSE", "datos al panel y notificaciones en vivo"],
            ["Usuario", "panel web", "operación, histórico y control remoto"],
            ["Usuario", "ThingSpeak", "visualización en la nube y comandos remotos"],
        ],
        anchos=[2.8, 4.6, 9.2],
        pie="Componentes del sistema y su responsabilidad principal.",
    )

    manual.h2("3.3 Decisiones de diseño")
    manual.h3("Un backend entre el dispositivo y la nube")
    manual.parrafo("El ESP32 podría publicar directamente en ThingSpeak, pero se descartó "
                   "por tres razones: SQLite no cabe en el microcontrolador, los comandos "
                   "necesitan validación y auditoría, y el panel debe seguir siendo útil si "
                   "la nube falla. El backend actúa como autoridad de datos: sella las "
                   "marcas de tiempo, decide qué comandos son válidos y conserva el "
                   "histórico local.")
    manual.h3("Cliente MQTT escrito a mano")
    manual.parrafo("No existen clientes MQTT para MicroPython en el ESP32 simulado, así que "
                   "`mqtt_client.py` implementa MQTT 3.1.1 sobre `asyncio.open_connection`: "
                   "CONNECT con Last Will, SUBSCRIBE/SUBACK, PUBLISH QoS 0 y 1 con PUBACK, "
                   "PINGREQ/PINGRESP y reconexión con retroceso exponencial. La mitad del "
                   "módulo son funciones puras de codificación, verificadas byte a byte en "
                   "las pruebas.")
    manual.h3("Concurrencia cooperativa con asyncio")
    manual.parrafo("El nodo ejecuta siete tareas independientes sobre un único bucle de "
                   "eventos. Ninguna bloquea a las demás: una lectura lenta del DHT22 no "
                   "retrasa la vigilancia del PIR, porque cada sensor tiene su periodo y su "
                   "turno en el bucle.")
    manual.h3("SQLite con un único escritor")
    manual.parrafo("Todas las escrituras pasan por un `asyncio.Lock` y se ejecutan en un "
                   "hilo aparte con `journal_mode=WAL`. Así se evita el clásico "
                   "`database is locked` sin renunciar a un motor embebido.")
    manual.h3("SSE en lugar de WebSocket")
    manual.parrafo("El panel solo necesita recibir datos. Server-Sent Events ofrece "
                   "reconexión nativa del navegador, menor complejidad y cero dependencias "
                   "adicionales.")

    manual.h2("3.4 Flujo de datos")
    manual.parrafo("El recorrido completo de una lectura y de un comando se detalla en la "
                   "figura siguiente. Los pasos 1 a 10 corresponden a la subida de datos y "
                   "los pasos 9 a 14 al camino de vuelta de un comando.")
    manual.figura(IMG / "flujo_datos.png",
                  "Flujo de datos entre el nodo, el broker, el backend y el panel, con los "
                  "tópicos MQTT en cada cruce.", ancho_cm=15.4)
    manual.tabla(
        ["Etapa", "Qué ocurre", "Dónde"],
        [
            ["1–2", "lectura del sensor, filtrado por mediana y validación de rango",
             "`sensors.py`"],
            ["3–4", "la FSM decide y se aplican los efectos sobre los actuadores",
             "`fsm.py`, `app.py`"],
            ["5–6", "publicación en `.../telemetry` (QoS 0) y reparto por el broker",
             "`mqtt_client.py`, HiveMQ"],
            ["7–8", "recepción, decodificación y almacenamiento con marca de tiempo",
             "`mqtt_bridge.py`, `storage.py`"],
            ["9–10", "evento SSE al navegador y redibujado de la gráfica",
             "`bus.py`, `app.js`"],
            ["11–14", "comando validado, publicado, ejecutado y confirmado con ACK",
             "`commands.py`, `app.py`"],
        ],
        anchos=[2.2, 11.0, 3.4],
        alinear_centro=(0,),
        pie="Etapas del flujo de datos.",
    )

    # ------------------------------------------------------- 4. requisitos
    manual.h1("4. Requisitos técnicos")

    manual.h2("4.1 Hardware del nodo")
    manual.parrafo("El circuito usa un ESP32 DevKit C V4 y diez módulos. Los GPIO del "
                   "diagrama coinciden exactamente con las constantes de "
                   "`firmware/config.py`, de modo que un cambio de cable exige cambiar una "
                   "sola línea de código.")
    manual.figura(IMG / "circuito.png",
                  "Esquema de conexiones del nodo: ESP32, cuatro sensores, cuatro "
                  "actuadores, OLED y pulsador.", ancho_cm=15.6)
    manual.tabla(
        ["Componente", "Tipo", "Conexión", "GPIO"],
        [
            ["DHT22", "sensor digital", "VCC · SDA · GND", "3V3 · **27** · GND"],
            ["PIR HC-SR501", "sensor digital", "VCC · OUT · GND", "3V3 · **26** · GND"],
            ["HC-SR04", "sensor ultrasónico", "VCC · TRIG · ECHO · GND",
             "3V3 · **5** · **18** · GND"],
            ["LDR (módulo)", "sensor analógico", "VCC · AO · GND", "3V3 · **34** · GND"],
            ["LED rojo", "actuador", "ánodo · cátodo", "**23** (220 Ω) · GND"],
            ["LED verde", "actuador", "ánodo · cátodo", "**19** (220 Ω) · GND"],
            ["Buzzer pasivo", "actuador PWM", "+ · −", "**25** · GND"],
            ["Servo SG90", "actuador PWM", "PWM · V+ · GND", "**13** · 3V3 · GND"],
            ["OLED SSD1306", "salida I2C", "SDA · SCL · VCC · GND",
             "**21** · **22** · 3V3 · GND"],
            ["Pulsador", "entrada", "terminal 1 · 2", "**4** · GND"],
        ],
        anchos=[3.4, 3.4, 5.4, 4.4],
        pie="Conexionado del nodo. El GPIO34 es solo entrada, apto para el LDR.",
    )
    manual.nota("En hardware real, el HC-SR04 y el servo se alimentan a **5 V** y el pin "
                "`ECHO` del sensor entrega 5 V: hay que intercalar un divisor de tensión "
                "antes del GPIO18. El DHT22 requiere una resistencia de *pull-up* de "
                "10 kΩ en la línea de datos.", "aviso")

    manual.h2("4.2 Software")
    manual.tabla(
        ["Componente", "Versión probada", "Uso"],
        [
            ["Python", "3.15.2 (mínimo 3.10)", "backend, pruebas y herramientas"],
            ["aiohttp", "3.14.5", "servidor web, API REST y SSE"],
            ["paho-mqtt", "2.2.0", "cliente MQTT del backend"],
            ["python-dotenv", "1.2.4", "lectura opcional del archivo `.env`"],
            ["pytest / pytest-asyncio", "9.2.0 / 1.5.0", "pruebas automatizadas"],
            ["Pillow", "13.0.0", "diagramas y capturas (solo desarrollo)"],
            ["MicroPython", "incluido en Wokwi", "firmware del ESP32"],
            ["Chrome o Edge", "versión actual", "panel y capturas automatizadas"],
        ],
        anchos=[4.6, 5.0, 7.0],
        pie="Dependencias y versiones con las que se validó el sistema.",
    )

    manual.h2("4.3 Red y puertos")
    manual.tabla(
        ["Puerto", "Protocolo", "Dirección", "Para qué"],
        [
            ["1883", "MQTT", "saliente al broker", "telemetría, eventos y comandos"],
            ["8883", "MQTT sobre TLS", "saliente (opcional)", "HiveMQ Cloud con cifrado"],
            ["8000", "HTTP", "entrante al panel", "API REST, SSE y archivos estáticos"],
            ["443", "HTTPS", "saliente", "API de ThingSpeak"],
        ],
        anchos=[2.2, 4.0, 4.6, 5.8],
        alinear_centro=(0,),
        pie="Puertos usados por el sistema.",
    )
    manual.parrafo("El nodo necesita salida a Internet hacia el broker. El panel puede "
                   "publicarse detrás de un proxy con TLS; el apartado 10.5 describe esa "
                   "configuración.")

    # ---------------------------------------------------------- 5. firmware
    manual.h1("5. Firmware del nodo")

    manual.h2("5.1 Estructura de módulos")
    manual.parrafo("El firmware son doce módulos planos (sin subcarpetas, porque el sistema "
                   "de archivos del simulador es más simple así) y cada uno tiene una única "
                   "responsabilidad:")
    manual.tabla(
        ["Módulo", "Responsabilidad", "Líneas aprox."],
        [
            ["`main.py`", "arranque: pantalla, WiFi, componentes y controlador", "70"],
            ["`config.py`", "pines, umbrales, tiempos, tópicos y credenciales", "125"],
            ["`hal.py`", "único punto que toca `machine` (Pin, PWM, ADC, I2C, DHT)", "230"],
            ["`bus.py`", "bus de eventos asíncrono con buzones acotados", "75"],
            ["`fsm.py`", "máquina de estados pura, sin hardware ni red", "260"],
            ["`sensors.py`", "DHT22, PIR, HC-SR04 y LDR con validación y mediana", "230"],
            ["`actuators.py`", "LEDs, sirena PWM y cerradura con servo", "160"],
            ["`ssd1306.py`", "driver mínimo del OLED sobre `framebuf`", "120"],
            ["`display.py`", "interfaz local: estado, lecturas y enlace", "135"],
            ["`mqtt_client.py`", "cliente MQTT 3.1.1 sobre asyncio streams", "430"],
            ["`net.py`", "WiFi con reintentos y estado de la señal", "110"],
            ["`app.py`", "controlador: tareas asíncronas y aplicación de efectos", "470"],
        ],
        anchos=[3.6, 10.6, 2.4],
        alinear_centro=(2,),
        pie="Módulos del firmware.",
    )

    manual.h2("5.2 Capa de abstracción de hardware")
    manual.parrafo("Todo el uso de `machine` está concentrado en `hal.py`. Los demás módulos "
                   "reciben objetos por inyección, lo que permite probar la lógica en "
                   "CPython con dobles y cambiar de placa tocando un solo archivo. Cada "
                   "envoltorio resuelve además las diferencias entre versiones de "
                   "MicroPython:")
    manual.codigo(
        """class PWM:
    \"\"\"PWM con compatibilidad entre versiones de MicroPython.\"\"\"

    def duty(self, valor=None):
        obj = self._instancia()
        if valor is None:
            return obj.duty()
        if hasattr(obj, "duty_u16"):
            obj.duty_u16(int(valor * 65535 / 1023))
        else:
            obj.duty(int(valor))
        return valor"""
    )
    manual.parrafo("El cliente MQTT, los sensores y los actuadores nunca importan "
                   "`machine` directamente, así que las pruebas pueden ejecutarse en un "
                   "computador sin placas.")

    manual.h2("5.3 Máquina de estados de seguridad")
    manual.parrafo("La lógica de seguridad es una máquina de estados pura: recibe el "
                   "instante actual y un evento, y devuelve una lista de **efectos** "
                   "(`sirena_on`, `abrir_cerradura`, `registrar_alerta`, …). No toca "
                   "hardware ni red, por eso se prueba entera con 39 casos automatizados.")
    manual.figura(IMG / "fsm.png",
                  "Estados y transiciones de la máquina de seguridad.", ancho_cm=15.2)
    manual.tabla(
        ["Estado", "Significado", "Sirena", "Cerradura"],
        [
            ["`DISARMED`", "sistema desactivado", "apagada", "se abre con PIN"],
            ["`ARMING`", "cuenta regresiva de salida (10 s)", "apagada", "cerrada"],
            ["`ARMED`", "vigilando", "apagada", "cerrada"],
            ["`ALARM`", "intrusión confirmada", "activa", "cerrada"],
        ],
        anchos=[3.4, 7.6, 2.6, 3.0],
        pie="Estados de la máquina de seguridad.",
    )
    manual.parrafo("Reglas implementadas:")
    manual.vinetas([
        "La cerradura solo se abre en `DISARMED` y con el PIN correcto.",
        "Tres PIN erróneos bloquean el comando durante 30 segundos.",
        "La cerradura se cierra sola 8 segundos después de abrirse.",
        "La sirena se calla sola a los 120 segundos si nadie desarma.",
        "Una alerta nueva necesita 5 segundos de separación: un PIR que queda en alto "
        "varios segundos no genera decenas de alertas.",
        "La temperatura por encima de 45 °C también dispara la alarma si el sistema está "
        "armado; si está desarmado solo registra un aviso.",
    ])
    manual.codigo(
        """def _presencia(self, ahora, evento):
    if self.estado not in (ARMADO, ALARMA):
        return []
    if not self._puede_alertar(ahora):        # antirrebote de 5 s
        return []
    self._ultima_alerta = ahora
    self.alertas += 1
    self.estado = ALARMA
    efectos = [_fx(FX_ALERTA, motivo=motivo, cm=distancia)]
    if not self.silenciada:
        self.sonando = True
        efectos.append(_fx(FX_SIRENA_ON))
    return efectos"""
    )

    manual.h2("5.4 Tareas asíncronas y bus de eventos")
    manual.parrafo("El controlador lanza siete tareas cooperativas. Cada una tiene un "
                   "periodo y una responsabilidad; ninguna usa esperas bloqueantes.")
    manual.tabla(
        ["Tarea", "Periodo", "Qué hace"],
        [
            ["`_bucle_mqtt`", "evento", "conecta, se suscribe y vigila la caída del enlace"],
            ["`_bucle_sensores`", "50 ms", "lee sensores, avanza la FSM y aplica efectos"],
            ["`_bucle_telemetria`", "5 s", "publica el estado de los sensores"],
            ["`_bucle_leds`", "100 ms", "parpadeos y tono bitonal de la sirena"],
            ["`_bucle_pantalla`", "600 ms", "refresca el OLED"],
            ["`_bucle_comandos`", "evento", "procesa comandos llegados del bus"],
            ["`_bucle_boton`", "50 ms", "antirrebote del pulsador físico"],
        ],
        anchos=[4.4, 2.4, 9.8],
        alinear_centro=(1,),
        pie="Tareas del controlador.",
    )
    manual.parrafo("El bus de eventos (`bus.py`) desacopla productores y consumidores. Cada "
                   "suscriptor tiene un buzón acotado: si se llena, se descarta el evento "
                   "más viejo, de modo que un consumidor lento nunca bloquea al resto del "
                   "sistema.")

    manual.h2("5.5 Sensores")
    manual.parrafo("Cada sensor valida sus lecturas y descarta valores imposibles. La "
                   "mediana de tres muestras elimina picos y el sistema conserva la última "
                   "lectura válida cuando un sensor falla, contando el error en lugar de "
                   "propagarlo.")
    manual.tabla(
        ["Sensor", "Periodo", "Tratamiento"],
        [
            ["DHT22", "5 s", "hasta 3 reintentos, mediana de 3, rangos −20…80 °C y 0…100 %"],
            ["PIR", "150 ms", "antirrebote con retención de 1,5 s"],
            ["HC-SR04", "500 ms", "mediana de 3 disparos, descarta ecos fuera de 2–350 cm"],
            ["LDR", "1 s", "conversión de ADC a lux con el modelo del módulo"],
        ],
        anchos=[3.0, 2.4, 11.2],
        alinear_centro=(1,),
        pie="Periodos y validación de cada sensor.",
    )
    manual.parrafo("La luminosidad se calcula con el modelo del módulo (resistencia fija "
                   "de 10 kΩ arriba y LDR a tierra):")
    manual.codigo(
        """V      = raw / max_raw * VCC
R_LDR  = serie * V / (VCC - V)
lux    = (RL10 * 10 ** gamma / R_LDR) ** (1 / gamma)"""
    )
    manual.nota("Con mucha luz el LDR baja su resistencia, la tensión de AO baja y el valor "
                "del ADC disminuye; en oscuridad el ADC sube y los lux tienden a cero. Una "
                "implementación con el divisor invertido devolvería valores altos en "
                "oscuridad; por eso el cálculo está cubierto por pruebas.", "aviso")

    manual.h2("5.6 Actuadores")
    manual.tabla(
        ["Actuador", "Control", "Detalle"],
        [
            ["LED rojo", "digital", "parpadeo a 2 Hz en alarma"],
            ["LED verde", "digital", "fijo al armarse, parpadeo a 4 Hz en la cuenta regresiva"],
            ["Sirena", "PWM", "tono bitonal de 2,4–2,9 kHz que alterna cada 300 ms"],
            ["Cerradura", "PWM 50 Hz", "0° cerrada y 90° abierta (500–2500 µs)"],
            ["OLED", "I2C", "estado, lecturas, cerradura, sirena y enlace"],
        ],
        anchos=[3.0, 3.0, 10.6],
        pie="Actuadores del nodo.",
    )
    manual.parrafo("El servo se posiciona convirtiendo el ángulo a ciclo de trabajo del "
                   "periodo de 20 ms:")
    manual.codigo(
        """ancho_us = min_us + (max_us - min_us) * (angulo / 180)
duty_u16 = int(ancho_us / 20000 * 65535)"""
    )

    manual.h2("5.7 Cliente MQTT del dispositivo")
    manual.parrafo("`mqtt_client.py` implementa lo necesario para el sistema: CONNECT con "
                   "Last Will, SUBSCRIBE/SUBACK, PUBLISH en QoS 0 y 1 con espera de PUBACK, "
                   "PINGREQ para el keepalive y reconexión con retroceso exponencial "
                   "(2 s hasta 60 s).")
    manual.tabla(
        ["Elemento", "Implementación"],
        [
            ["CONNECT", "protocolo MQTT nivel 4, sesión limpia, LWT `offline` retenido"],
            ["PUBLISH QoS 1", "identificador de paquete, espera de PUBACK con tiempo límite"],
            ["SUBSCRIBE", "suscripción a `.../cmd` y `.../config` con QoS 1"],
            ["Keepalive", "PINGREQ cada `keepalive/2`; si no hay respuesta, se reconecta"],
            ["Reconexión", "`conectar_con_reintentos` con retroceso exponencial"],
            ["Callback", "solo publica en el bus: nunca bloquea el hilo de lectura"],
        ],
        anchos=[3.6, 13.0],
        pie="Elementos del protocolo cubiertos por el cliente.",
    )
    manual.codigo(
        """def encode_connect(client_id, keepalive=30, will_topic=None, will_msg=None,
                   will_qos=1, will_retain=True, usuario=None, clave=None,
                   clean=True):
    flags = 0
    if clean:
        flags |= 0x02
    if will_topic is not None:
        flags |= 0x04 | ((will_qos & 0x03) << 3)
        if will_retain:
            flags |= 0x20
    ..."""
    )

    manual.h2("5.8 Arranque del nodo")
    manual.parrafo("El orden de arranque está pensado para que el nodo dé señales de vida "
                   "aunque falle la red: primero la pantalla, después el WiFi y por último "
                   "los servicios.")
    manual.numerada([
        "Se crea la pantalla y se muestra el aviso «Iniciando…».",
        "Se conecta el WiFi con reintentos (`net.Wifi.conectar`).",
        "Se construyen actuadores, sensores y la máquina de estados.",
        "Se crea el cliente MQTT con sus credenciales y el Last Will.",
        "El controlador lanza sus tareas y queda a la escucha.",
    ])

    manual.h2("5.9 Configuración del firmware")
    manual.parrafo("Todos los valores ajustables viven en `firmware/config.py`; no hay "
                   "números mágicos repartidos por el código. Los más relevantes:")
    manual.tabla(
        ["Constante", "Valor", "Efecto"],
        [
            ["`DEVICE_ID`", "`dev01`", "identificador en los tópicos y en la base de datos"],
            ["`MQTT_HOST` / `MQTT_PORT`", "`broker.hivemq.com` / `1883`", "broker público"],
            ["`TELEMETRY_PERIOD_S`", "5", "frecuencia de publicación"],
            ["`EXIT_DELAY_S`", "10", "tiempo para salir antes de armarse"],
            ["`DIST_ALARM_CM`", "80", "presencia más cerca que esto dispara alarma"],
            ["`TEMP_ALARM_C`", "45", "umbral de sobrecalentamiento"],
            ["`SIREN_MAX_S`", "120", "tiempo máximo de sirena sin desarmar"],
            ["`AUTO_RELOCK_S`", "8", "cierre automático de la cerradura"],
            ["`UNLOCK_PIN`", "`2468`", "PIN de apertura (cambiar en producción)"],
            ["`PIN_INTENTOS_MAX`", "3", "intentos antes del bloqueo"],
            ["`PIN_BLOQUEO_S`", "30", "duración del bloqueo"],
        ],
        anchos=[4.6, 4.6, 7.4],
        pie="Constantes principales del firmware.",
    )

    # ------------------------------------------------------ 6. protocolo MQTT
    manual.h1("6. Protocolo MQTT")

    manual.h2("6.1 Tópicos")
    manual.parrafo("El prefijo es configurable y el identificador de dispositivo forma parte "
                   "del tópico, de modo que el backend admite varios nodos sin cambios:")
    manual.codigo("centinela/<device_id>/<canal>")
    manual.tabla(
        ["Tópico", "Dirección", "QoS", "Retenido", "Contenido"],
        [
            ["`centinela/dev01/telemetry`", "nodo → backend", "0", "no", "lecturas de sensores"],
            ["`centinela/dev01/events`", "nodo → backend", "1", "no", "alarmas y cambios de estado"],
            ["`centinela/dev01/status`", "nodo → backend", "1", "sí", "`online` / `offline` (LWT)"],
            ["`centinela/dev01/cmd`", "backend → nodo", "1", "no", "comandos"],
            ["`centinela/dev01/ack`", "nodo → backend", "1", "no", "confirmación con resultado"],
            ["`centinela/dev01/config`", "backend → nodo", "1", "no", "cambio de umbrales"],
        ],
        anchos=[5.2, 3.4, 1.4, 1.8, 4.8],
        alinear_centro=(2, 3),
        pie="Tópicos MQTT del sistema.",
    )
    manual.parrafo("QoS 0 para telemetría porque una lectura perdida se recupera con la "
                   "siguiente; QoS 1 para eventos, comandos y confirmaciones porque "
                   "perderlos cambia el estado del sistema.")

    manual.h2("6.2 Telemetría")
    manual.codigo(
        """{
  "v": 1, "device": "dev01", "name": "Centinela-Puerta-Principal",
  "seq": 42, "uptime_s": 210,
  "temp_c": 24.6, "hum_pct": 58.0, "lux": 63.0, "dist_cm": 118.0,
  "motion": false, "state": "ARMED", "alarm": false, "siren": false,
  "locked": true, "alerts": 2, "rssi": -55,
  "sensor_errors": 0, "fw": "2.0.0"
}"""
    )
    manual.tabla(
        ["Campo", "Tipo", "Descripción"],
        [
            ["`v`", "entero", "versión del contrato de datos"],
            ["`device` / `name`", "texto", "identificador y nombre del nodo"],
            ["`seq`", "entero", "número de secuencia creciente"],
            ["`uptime_s`", "entero", "segundos desde el arranque (el nodo no tiene reloj)"],
            ["`temp_c` / `hum_pct`", "real / nulo", "temperatura y humedad del DHT22"],
            ["`lux`", "real / nulo", "luminosidad calculada desde el LDR"],
            ["`dist_cm`", "real / nulo", "distancia medida por el HC-SR04"],
            ["`motion`", "booleano", "movimiento detectado por el PIR"],
            ["`state`", "texto", "estado de la FSM"],
            ["`alarm` / `siren` / `locked`", "booleano", "alarma, sirena y cerradura"],
            ["`alerts`", "entero", "alertas acumuladas desde el arranque"],
            ["`rssi`", "entero", "potencia de señal WiFi en dBm"],
            ["`sensor_errors`", "entero", "lecturas fallidas acumuladas"],
        ],
        anchos=[4.6, 3.0, 9.0],
        pie="Campos de la trama de telemetría.",
    )

    manual.h2("6.3 Eventos")
    manual.codigo(
        """{
  "v": 1, "device": "dev01", "kind": "intrusion", "severity": "critical",
  "message": "Alerta: presencia_cercana", "uptime_s": 215, "state": "ALARM",
  "data": {"cm": 42.5, "alerts": 1}
}"""
    )
    manual.tabla(
        ["`kind`", "Cuándo se emite"],
        [
            ["`state`", "cambio de estado de la máquina de seguridad"],
            ["`intrusion`", "presencia detectada estando armado"],
            ["`alarm` / `alarm_off`", "sirena activada o silenciada"],
            ["`lock` / `unlock`", "cerradura cerrada o abierta"],
            ["`command` / `command_rejected`", "comando ejecutado o rechazado"],
            ["`network`", "conexión o pérdida del enlace MQTT"],
            ["`config`", "umbrales actualizados en caliente"],
        ],
        anchos=[5.2, 11.4],
        pie="Tipos de evento.",
    )
    manual.parrafo("Las severidades son `info`, `warning` y `critical`; el backend registra "
                   "todas y destaca las dos últimas en el feed del panel.")

    manual.h2("6.4 Comandos y confirmación")
    manual.codigo(
        """{"v":1,"id":"9f2c1a7b3d40","cmd":"unlock","args":{"pin":"2468"},"source":"panel"}
{"v":1,"id":"9f2c1a7b3d40","cmd":"unlock","ok":true,"state":"DISARMED",
 "locked":false,"alerts":0,"result":{"locked":false,"auto_relock_s":8}}"""
    )
    manual.tabla(
        ["Comando", "Argumentos", "Validación en el backend", "Efecto en el nodo"],
        [
            ["`arm`", "—", "sin argumentos", "inicia la cuenta regresiva y cierra la cerradura"],
            ["`disarm`", "—", "sin argumentos", "desarma y apaga la sirena"],
            ["`mute`", "—", "solo en alarma", "silencia sin desarmar"],
            ["`unlock`", "`pin` de 4 a 8 dígitos", "PIN numérico y longitud", "abre 8 s si está desarmado"],
            ["`ping`", "—", "sin argumentos", "responde con el uptime"],
            ["`set_config`", "umbrales numéricos", "rangos por clave", "actualiza la FSM en caliente"],
        ],
        anchos=[2.6, 3.6, 5.0, 5.4],
        pie="Comandos admitidos y su validación.",
    )
    manual.parrafo("Rangos aceptados en `set_config`:")
    manual.tabla(
        ["Clave", "Mínimo", "Máximo", "Unidad"],
        [
            ["`dist_alarm_cm`", "10", "350", "cm"],
            ["`exit_delay_s`", "0", "300", "s"],
            ["`temp_alarm_c`", "10", "120", "°C"],
            ["`auto_relock_s`", "1", "120", "s"],
            ["`siren_max_s`", "5", "900", "s"],
        ],
        anchos=[5.0, 3.0, 3.0, 3.0],
        alinear_centro=(1, 2, 3),
        pie="Rangos válidos para el cambio de umbrales.",
    )

    manual.h2("6.5 Motivos de rechazo")
    manual.parrafo("Todo comando rechazado devuelve un motivo legible, que el panel traduce "
                   "a un mensaje para el operador:")
    manual.tabla(
        ["Motivo", "Origen", "Significado"],
        [
            ["`comando_no_permitido`", "backend", "no está en la lista blanca"],
            ["`argumentos_invalidos`", "backend", "los argumentos no son un objeto"],
            ["`pin_invalido`", "backend", "PIN no numérico o de longitud incorrecta"],
            ["`config_fuera_de_rango`", "backend", "umbral fuera de los límites"],
            ["`demasiados_comandos`", "backend", "más de 30 comandos por minuto"],
            ["`sin_conexion_mqtt`", "backend", "no hay enlace con el broker"],
            ["`publicacion_fallida`", "backend", "el broker no aceptó la publicación"],
            ["`timeout`", "backend", "el nodo no confirmó en 8 segundos"],
            ["`sistema_armado`", "nodo", "se intentó abrir con el sistema armado"],
            ["`pin_incorrecto`", "nodo", "el PIN no coincide"],
            ["`bloqueado` / `pin_bloqueado`", "nodo", "bloqueo temporal por intentos fallidos"],
        ],
        anchos=[5.6, 2.6, 8.4],
        pie="Motivos de rechazo y su origen.",
    )

    # ----------------------------------------------------------- 7. backend
    manual.h1("7. Backend de servicios")

    manual.h2("7.1 Estructura")
    manual.tabla(
        ["Módulo", "Responsabilidad"],
        [
            ["`main.py`", "compone servicios, arranca tareas y sirve el panel"],
            ["`config.py`", "configuración por entorno y archivo `.env`"],
            ["`mqtt_bridge.py`", "paho-mqtt en un hilo, adaptado a asyncio"],
            ["`storage.py`", "DAO SQLite con un único escritor"],
            ["`commands.py`", "validación, envío, ACK y auditoría"],
            ["`cloud.py`", "ThingSpeak: canal de 8 campos y TalkBack"],
            ["`bus.py`", "eventos en proceso para SSE"],
            ["`web/app.py`", "API REST, SSE, login y archivos estáticos"],
            ["`web/auth.py`", "cookie de sesión firmada con HMAC-SHA256"],
            ["`cli.py`", "consultas de históricos por consola"],
        ],
        anchos=[4.2, 12.4],
        pie="Módulos del backend.",
    )

    manual.h2("7.2 Concurrencia")
    manual.parrafo("El backend corre sobre un único bucle de eventos. paho-mqtt trabaja en "
                   "un hilo propio y sus callbacks depositan los mensajes en una cola "
                   "asíncrona con `call_soon_threadsafe`, de modo que el resto del sistema "
                   "nunca ve hilos.")
    manual.codigo(
        """def _al_recibir(self, cliente, userdata, mensaje):
    loop = self._loop
    if loop is None:
        return
    datos = {"topic": mensaje.topic, "payload": bytes(mensaje.payload),
             "qos": mensaje.qos, "retain": bool(mensaje.retain)}
    loop.call_soon_threadsafe(self._cola.put_nowait, (mensaje.topic, datos))"""
    )
    manual.tabla(
        ["Tarea", "Periodo", "Función"],
        [
            ["`_bucle_mensajes`", "evento", "procesa telemetría, eventos, estado y ACK"],
            ["`_bucle_talkback`", "15 s", "recoge comandos de ThingSpeak"],
            ["`_bucle_mantenimiento`", "5 s / 1 h", "expira comandos y purga datos antiguos"],
        ],
        anchos=[5.0, 3.0, 8.6],
        alinear_centro=(1,),
        pie="Tareas de fondo del backend.",
    )

    manual.h2("7.3 Servicio de comandos")
    manual.parrafo("El ciclo de vida de un comando garantiza que nunca quede «en el aire»:")
    manual.numerada([
        "Validación de lista blanca, tipos y rangos.",
        "Límite de frecuencia por origen (30 comandos por minuto).",
        "Registro en la tabla `commands` con estado `PENDIENTE` **antes** de publicar.",
        "Publicación en `.../cmd` con QoS 1 e identificador único de 12 caracteres.",
        "Espera del ACK con tiempo límite de 8 segundos.",
        "Cierre como `OK`, `RECHAZADO`, `TIMEOUT` o `ERROR`, guardando la latencia.",
    ])
    manual.parrafo("Los ACK con identificadores desconocidos se descartan, lo que evita que "
                   "una respuesta falsa cierre un comando ajeno.")

    manual.h2("7.4 Integración con la nube")
    manual.parrafo("ThingSpeak recibe una lectura cada 20 segundos (el plan gratuito admite "
                   "una cada 15) y devuelve comandos por TalkBack cada 15 segundos. Los "
                   "ocho campos del canal son:")
    manual.tabla(
        ["Campo", "Contenido", "Rango"],
        [
            ["`field1`", "temperatura (°C)", "−20 … 80"],
            ["`field2`", "humedad (%)", "0 … 100"],
            ["`field3`", "luminosidad (lux)", "0 … 100 000"],
            ["`field4`", "distancia (cm)", "2 … 350"],
            ["`field5`", "movimiento", "0 / 1"],
            ["`field6`", "alarma", "0 / 1"],
            ["`field7`", "estado (código)", "0 … 3"],
            ["`field8`", "alertas acumuladas", "entero"],
        ],
        anchos=[2.6, 7.0, 7.0],
        pie="Campos del canal de ThingSpeak.",
    )
    manual.parrafo("Los códigos de estado son `DISARMED`=0, `ARMING`=1, `ARMED`=2 y "
                   "`ALARM`=3. Si no hay claves configuradas, el sistema usa una "
                   "implementación nula y todo funciona en local.")

    manual.h2("7.5 API del panel")
    manual.parrafo("Todas las rutas de datos exigen sesión válida salvo en modo "
                   "demostración. Las respuestas son JSON y los errores incluyen un código "
                   "legible.")
    manual.tabla(
        ["Método y ruta", "Función"],
        [
            ["`GET /`", "panel del operador (redirige a `/login` sin sesión)"],
            ["`GET /login`, `POST /login`", "formulario de acceso y creación de la sesión"],
            ["`POST /logout`", "cierra la sesión"],
            ["`GET /healthz`", "estado del servicio (MQTT y clientes SSE conectados)"],
            ["`GET /api/estado`", "lectura actual, estado, MQTT, nube y comandos"],
            ["`GET /api/lecturas?horas=6`", "serie temporal y agregados por hora"],
            ["`GET /api/eventos?limite=40`", "últimos eventos, opcionalmente por severidad"],
            ["`GET /api/comandos?limite=25`", "comandos con estado y latencia"],
            ["`GET /api/estadisticas`", "agregados, alarmas y latencias"],
            ["`GET /api/estado-seguridad`", "transiciones de la máquina de estados"],
            ["`POST /api/comando`", "envía un comando y espera su ACK"],
            ["`GET /api/stream`", "canal SSE con los eventos en vivo"],
        ],
        anchos=[5.6, 11.0],
        pie="Rutas de la API del panel.",
    )
    manual.codigo(
        """POST /api/comando
{"cmd": "unlock", "args": {"pin": "2468"}}

200 OK
{"ok": true, "id": "9f2c1a7b3d40", "motivo": null,
 "ack": {"ok": true, "state": "DISARMED", "locked": false,
         "result": {"locked": false, "auto_relock_s": 8}}}"""
    )

    manual.h2("7.6 Sesiones")
    manual.parrafo("La sesión es una cookie firmada con HMAC-SHA256 que contiene el usuario "
                   "y la caducidad; el servidor no guarda estado. La comparación de firma y "
                   "de credenciales usa `hmac.compare_digest` para no filtrar información "
                   "por tiempo de respuesta. La cookie es `HttpOnly`, `SameSite=Lax` y dura "
                   "ocho horas.")

    # ------------------------------------------------------ 8. base de datos
    manual.h1("8. Base de datos")

    manual.h2("8.1 Modelo de datos")
    manual.parrafo("SQLite en modo WAL con cinco tablas, cinco vistas y siete índices. Las "
                   "marcas de tiempo se guardan dos veces: `ts_epoch` (real, para cálculos "
                   "e índices) y `ts_utc` (texto ISO-8601, para lectura humana).")
    manual.figura(IMG / "modelo_datos.png",
                  "Modelo entidad-relación de la base de datos.", ancho_cm=15.4)
    manual.tabla(
        ["Tabla", "Contenido", "Filas típicas"],
        [
            ["`devices`", "nodos registrados y última vez vistos", "una por dispositivo"],
            ["`readings`", "una fila por mensaje de telemetría", "≈ 17 000 al día"],
            ["`events`", "alarmas, cambios de estado, red y comandos", "decenas al día"],
            ["`commands`", "comandos con estado, latencia y motivo", "según el uso"],
            ["`state_changes`", "transiciones de la máquina de seguridad", "pocas al día"],
        ],
        anchos=[3.2, 9.4, 4.0],
        pie="Tablas de la base de datos.",
    )

    manual.h2("8.2 Vistas e índices")
    manual.tabla(
        ["Vista", "Para qué sirve"],
        [
            ["`v_ultima_lectura`", "estado actual de cada dispositivo"],
            ["`v_resumen_horario`", "promedios, mínimos y máximos por hora"],
            ["`v_salud_comandos`", "porcentaje de éxito y latencia por origen y día"],
            ["`v_eventos_criticos`", "eventos `warning` y `critical` ordenados"],
            ["`v_estado_actual`", "última transición de estado por dispositivo"],
        ],
        anchos=[4.4, 12.2],
        pie="Vistas de la base de datos.",
    )
    manual.parrafo("Los índices cubren los accesos reales del sistema: histórico por "
                   "dispositivo y fecha, episodios de alarma, feed de eventos, comandos por "
                   "estado y transiciones de estado. Sin ellos, las consultas de 24 horas "
                   "recorrerían la tabla completa.")

    manual.h2("8.3 Consultas de históricos")
    manual.parrafo("Las doce consultas documentadas viven en `sql/consultas.sql` y cubren "
                   "los casos de uso del panel y de la consola. Un ejemplo: detección de "
                   "huecos de telemetría, útil para saber si el nodo estuvo caído.")
    manual.codigo(
        """SELECT ts_utc, ROUND(siguiente - ts_epoch, 1) AS segundos_sin_datos
  FROM (SELECT ts_epoch, ts_utc,
               LEAD(ts_epoch) OVER (ORDER BY ts_epoch) AS siguiente
          FROM readings WHERE device_id = :device_id)
 WHERE siguiente - ts_epoch > 30
 ORDER BY ts_epoch DESC LIMIT 20;"""
    )
    manual.parrafo("El mantenimiento incluye una purga automática que conserva 30 días por "
                   "defecto (`RETENTION_DAYS`) y un comando manual de compactación.")

    # ---------------------------------------------------------- 9. seguridad
    manual.h1("9. Seguridad")

    manual.parrafo("El sistema no maneja datos personales, pero sí controla el acceso "
                   "físico a una vivienda, así que los controles se centran en la integridad "
                   "de los comandos y en la trazabilidad.")
    manual.tabla(
        ["Amenaza", "Control implementado"],
        [
            ["Comando arbitrario por MQTT", "lista blanca, tipos y rangos validados en el backend"],
            ["Abuso o ráfaga de comandos", "límite de 30 por minuto por origen"],
            ["Fuerza bruta del PIN", "3 intentos y bloqueo de 30 s en el nodo"],
            ["Comando perdido", "QoS 1, ACK obligatorio y estado `TIMEOUT` a los 8 s"],
            ["Suplantación del nodo", "LWT retenido: `offline` si desaparece"],
            ["Acceso al panel", "cookie firmada, `HttpOnly`, caducidad de 8 h"],
            ["Fuga por tiempo de respuesta", "`hmac.compare_digest` en firma y credenciales"],
            ["Inyección SQL", "100 % de consultas parametrizadas"],
            ["Escucha del tráfico", "TLS opcional para HiveMQ Cloud (`MQTT_TLS=1`, 8883)"],
        ],
        anchos=[5.0, 11.6],
        pie="Modelo de amenazas y controles.",
    )
    manual.nota("El broker público de HiveMQ no exige autenticación y cualquiera puede "
                "publicar en los tópicos. Para uso real hay que crear un clúster en HiveMQ "
                "Cloud, activar TLS y credenciales, y cambiar `UNLOCK_PIN` y "
                "`SECRET_KEY`.", "peligro")
    manual.parrafo("El panel se sirve por HTTP en la red local. Si se publica fuera, debe "
                   "hacerse detrás de un proxy con TLS y, preferiblemente, con una lista de "
                   "direcciones permitidas.")

    manual.h2("9.1 Lista de verificación antes de producción")
    manual.parrafo("Antes de usar el sistema en una vivienda real conviene repasar estos "
                   "puntos. Ninguno es opcional si el equipo queda expuesto a Internet:")
    manual.tabla(
        ["#", "Comprobación", "Cómo"],
        [
            ["1", "Cambiar el PIN de la cerradura", "`UNLOCK_PIN` en `firmware/config.py`"],
            ["2", "Cambiar la contraseña del panel", "`WEB_PASSWORD` en `.env`"],
            ["3", "Cambiar la clave de firma de sesión", "`SECRET_KEY` en `.env`"],
            ["4", "Usar un broker autenticado", "clúster de HiveMQ Cloud y `MQTT_TLS=1`"],
            ["5", "Cifrar el panel", "proxy inverso con TLS delante de `WEB_PORT`"],
            ["6", "Limitar el acceso a la red", "reglas de firewall o VPN"],
            ["7", "Programar respaldos", "copia diaria del archivo `.db`"],
            ["8", "Revisar la retención", "`RETENTION_DAYS` según el uso"],
            ["9", "Probar la alarma", "una vez al mes, con aviso a los convivientes"],
            ["10", "Actualizar dependencias", "`pip install -r requirements.txt` tras revisar versiones"],
        ],
        anchos=[0.9, 6.6, 9.1],
        alinear_centro=(0,),
        pie="Lista de verificación de seguridad antes de producción.",
    )

    manual.h2("9.2 Qué queda registrado")
    manual.parrafo("La trazabilidad es parte del diseño: el sistema puede explicar qué pasó y "
                   "cuándo, no solo el estado actual.")
    manual.tabla(
        ["Se guarda", "Para qué"],
        [
            ["Cada lectura con fecha, hora y estado", "reconstruir la secuencia de una alarma"],
            ["Cada cambio de estado y su motivo", "saber quién armó o desarmó y por qué"],
            ["Cada comando con origen, resultado y latencia", "auditar accesos a la cerradura"],
            ["Cada evento con gravedad", "priorizar la revisión del operador"],
            ["Los errores de sensor acumulados", "detectar hardware degradado"],
        ],
        anchos=[7.2, 9.4],
        pie="Información conservada por el sistema.",
    )
    manual.nota("El PIN nunca se guarda en claro: en la auditoría de comandos solo consta que "
                "se envió el comando `unlock` y su resultado. Aun así, evite escribir el PIN "
                "en campos de texto libre.", "truco")

    # ------------------------------------------------- 10. instalacion
    manual.h1("10. Instalación y despliegue")

    manual.h2("10.1 Puesta en marcha del backend")
    manual.codigo(
        """cd Parcial2_IoT_Seguridad
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python -m backend.main --seed"""
    )
    manual.parrafo("El backend aplica el esquema, registra el dispositivo, conecta al broker, "
                   "arranca las tareas de fondo y sirve el panel en "
                   "`http://127.0.0.1:8000`. Las credenciales iniciales son `admin` / "
                   "`seguridad2026`.")
    manual.tabla(
        ["Opción", "Efecto"],
        [
            ["`--seed`", "carga 24 h de datos de demostración"],
            ["`--puerto 8010`", "cambia el puerto del panel"],
            ["`--sin-login`", "panel abierto, solo para demostraciones"],
            ["`--sin-mqtt`", "no intenta conectar al broker (modo offline)"],
            ["`--version`", "muestra la versión del backend"],
        ],
        anchos=[3.8, 12.8],
        pie="Opciones de arranque del backend.",
    )

    manual.h2("10.2 Variables de entorno")
    manual.parrafo("La configuración se lee del entorno y, si existe, del archivo `.env` "
                   "(plantilla en `.env.example`):")
    manual.tabla(
        ["Variable", "Valor por defecto", "Uso"],
        [
            ["`WEB_HOST` / `WEB_PORT`", "`127.0.0.1` / `8000`", "interfaz y puerto del panel"],
            ["`WEB_USER` / `WEB_PASSWORD`", "`admin` / `seguridad2026`", "credenciales"],
            ["`SECRET_KEY`", "(cambiar)", "firma de la cookie de sesión"],
            ["`SIN_LOGIN`", "`0`", "`1` abre el panel sin autenticación"],
            ["`DB_PATH`", "`data/centinela.db`", "ruta de la base SQLite"],
            ["`RETENTION_DAYS`", "`30`", "días conservados antes de purgar"],
            ["`MQTT_HOST` / `MQTT_PORT`", "`broker.hivemq.com` / `1883`", "broker"],
            ["`MQTT_TLS`", "`0`", "`1` para el puerto 8883"],
            ["`MQTT_USER` / `MQTT_PASSWORD`", "vacío", "credenciales del broker"],
            ["`TOPIC_PREFIX` / `DEVICE_ID`", "`centinela` / `dev01`", "espacio de tópicos"],
            ["`MQTT_ACK_TIMEOUT_S`", "`8`", "espera máxima del ACK"],
            ["`THINGSPEAK_CHANNEL` / `_WRITE_KEY`", "vacío", "canal de la nube"],
            ["`THINGSPEAK_TALKBACK_ID` / `_KEY`", "vacío", "cola de comandos remotos"],
        ],
        anchos=[5.6, 5.6, 5.4],
        pie="Variables de entorno del backend.",
    )

    manual.h2("10.3 Nodo en Wokwi")
    manual.numerada([
        "Entrar a <https://wokwi.com> y crear un proyecto **ESP32 / MicroPython**.",
        "Cargar los doce archivos del firmware y el `diagram.json` "
        "(`entregables/Wokwi_Centinela_IoT.zip`).",
        "Pulsar **Play**: el nodo se conecta a `Wokwi-GUEST` y publica en el broker.",
    ])
    manual.figura(CAP / "wokwi_01_circuito.png",
                  "Nodo simulado en Wokwi con el circuito completo en marcha.", ancho_cm=11.5)
    manual.figura(CAP / "wokwi_02_serie.png",
                  "Monitor serie del nodo: arranque, pantalla, WiFi y conexión MQTT.",
                  ancho_cm=15.4)

    manual.h2("10.4 ThingSpeak")
    manual.parrafo("Se crea un canal con ocho campos (tabla del apartado 7.4), se copian el "
                   "identificador y la clave de escritura al `.env`, y opcionalmente se "
                   "habilita la aplicación TalkBack para enviar comandos desde la nube. Los "
                   "detalles están en `docs/plataforma_nube.md`.")

    manual.h2("10.5 Puesta en producción")
    manual.parrafo("Para ejecutar el backend como servicio en Linux se usa una unidad de "
                   "systemd:")
    manual.codigo(
        """[Unit]
Description=Centinela IoT backend
After=network-online.target

[Service]
User=centinela
WorkingDirectory=/opt/centinela
EnvironmentFile=/opt/centinela/.env
ExecStart=/opt/centinela/.venv/bin/python -m backend.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"""
    )
    manual.parrafo("Recomendaciones adicionales: publicar el panel detrás de Nginx con TLS, "
                   "limitar el acceso por red o VPN, usar un clúster MQTT con credenciales, "
                   "respaldar el archivo `.db` a diario y rotar `SECRET_KEY` junto con las "
                   "claves de ThingSpeak.")

    # --------------------------------------------------------- 11. pruebas
    manual.h1("11. Pruebas y calidad")

    manual.h2("11.1 Estrategia")
    manual.parrafo("Las 314 pruebas se ejecutan en CPython sin placas ni simulador. El "
                   "firmware se prueba con dobles de `machine`, `dht`, `framebuf` y "
                   "`network`; el cliente MQTT se enfrenta a un broker falso que habla TCP "
                   "real; el backend usa SQLite real y el servidor aiohttp de pruebas.")
    manual.tabla(
        ["Archivo", "Casos", "Qué cubre"],
        [
            ["`test_fsm.py`", "39", "estados, temporizadores, PIN, antirrebote, efectos"],
            ["`test_mqtt.py`", "45", "codificación de paquetes y transporte contra broker falso"],
            ["`test_sensors.py`", "26", "mediana, reintentos, rangos y lux"],
            ["`test_app.py`", "28", "controlador, comandos, telemetría y recepción"],
            ["`test_actuators.py`", "18", "LEDs, sirena y servo"],
            ["`test_display.py`", "16", "pantalla, recorte y valores ausentes"],
            ["`test_storage.py`", "30", "lecturas, eventos, comandos y purga"],
            ["`test_commands.py`", "29", "validación, ACK, timeout y límite de frecuencia"],
            ["`test_bridge.py`", "30", "puente paho y bus de eventos"],
            ["`test_cloud.py`", "24", "canal de ThingSpeak y TalkBack"],
            ["`test_web.py`", "20", "API, sesión, SSE y archivos estáticos"],
            ["`test_auth.py`", "9", "firma, caducidad y manipulación de la cookie"],
        ],
        anchos=[4.2, 1.6, 10.8],
        alinear_centro=(1,),
        pie="Distribución de las 314 pruebas automatizadas.",
    )

    manual.h2("11.2 Cómo ejecutarlas")
    manual.codigo(
        """python -m pytest              # 314 pruebas, ~50 s
python -m pytest tests/test_fsm.py -q
python -m pytest -k "alarma" -v"""
    )
    manual.parrafo("Las pruebas dejaron de ser un trámite: encontraron defectos reales "
                   "durante el desarrollo, entre ellos una fórmula de lux invertida, un "
                   "`UPDATE` que devolvía el identificador en lugar de las filas afectadas, "
                   "la falta de clave foránea al registrar comandos y un cierre de socket "
                   "que se bloqueaba esperando una conexión abierta.")

    manual.h2("11.3 Demostración completa")
    manual.parrafo("Además de las pruebas unitarias existe una demo que arranca el backend "
                   "y un nodo emulado que ejecuta el código real del firmware:")
    manual.codigo(
        """python scripts\\demo.py --reset --sembrar --sin-login
python scripts\\demo.py --sin-mqtt --escenario intruso --duracion 60"""
    )
    manual.parrafo("La primera variante usa el broker real; la segunda conecta nodo y "
                   "backend en memoria y funciona sin Internet.")

    manual.h2("11.4 Limitaciones conocidas")
    manual.vinetas([
        "El nodo no tiene reloj de tiempo real: publica `uptime_s` y es el servidor el que "
        "sella cada lectura, para que un reinicio no rompa el histórico.",
        "En el simulador de Wokwi la lectura del **HC-SR04** no siempre entrega valores "
        "(`dist_cm` nulo y `sensor_errors` creciente); conviene verificar el disparo en el "
        "navegador antes de evaluar la detección por distancia.",
        "El botón *Simulate Motion* del PIR no siempre llega al firmware cuando la "
        "simulación corre en un navegador headless; en un navegador normal funciona.",
        "El broker público no está autenticado: es apto para prácticas, no para uso real.",
        "La telemetría cada 5 segundos genera unas 17 000 filas diarias; la purga conserva "
        "30 días por defecto.",
    ])

    # ------------------------------------------------- 12. operacion
    manual.h1("12. Operación y mantenimiento")

    manual.h2("12.1 Registro y diagnóstico")
    manual.tabla(
        ["Qué mirar", "Dónde"],
        [
            ["Arranque del nodo (WiFi, MQTT, pantalla)", "monitor serie de Wokwi"],
            ["Conexión del backend y suscripción", "salida de `python -m backend.main`"],
            ["Estado del broker y de la nube", "`GET /healthz` y tarjeta «Estado del sistema»"],
            ["Comandos pendientes o expirados", "`python -m backend.cli comandos`"],
            ["Eventos críticos", "`python -m backend.cli eventos --severidad critical`"],
        ],
        anchos=[8.4, 8.2],
        pie="Fuentes de diagnóstico.",
    )
    manual.codigo(
        """[10:23:11] MQTT conectado a broker.hivemq.com:1883
[10:23:11] suscrito a centinela/+/#
[10:23:17] nodo dev01: online
[10:23:29] EVENTO CRITICO: Alerta: presencia_cercana
[10:23:30] EVENTO CRITICO: Sirena activada"""
    )

    manual.h2("12.2 Respaldo y purga")
    manual.codigo(
        """:: respaldo en caliente (SQLite en modo WAL)
sqlite3 data/centinela.db ".backup 'respaldo-2026-11-14.db'"

:: purga manual de datos anteriores a 30 días
python -m backend.cli purgar --dias 30

:: compactar el archivo
sqlite3 data/centinela.db "VACUUM;\""""
    )

    manual.h2("12.3 Actualización del firmware")
    manual.parrafo("El firmware y el proyecto de Wokwi deben mantenerse sincronizados. "
                   "Tras modificar cualquier archivo de `firmware/`:")
    manual.numerada([
        "Ejecutar las pruebas (`python -m pytest`).",
        "Regenerar el paquete de Wokwi (`python scripts\\empaquetar.py`).",
        "Actualizar los archivos en el proyecto de Wokwi o reimportar el ZIP.",
        "Verificar en el monitor serie que el nodo arranca y publica.",
    ])
    manual.nota("Si se cambia el contrato de datos (campos de telemetría o comandos), hay "
                "que actualizar a la vez el firmware y el backend, y subir la versión del "
                "protocolo (`PROTOCOL_VERSION`).", "aviso")

    manual.h2("12.4 Solución de problemas")
    manual.tabla(
        ["Síntoma", "Causa probable", "Solución"],
        [
            ["Panel con «MQTT OFF»", "broker inalcanzable o firewall", "probar `--sin-mqtt`; revisar salida a Internet"],
            ["No hay lecturas nuevas", "el nodo no publica", "revisar monitor serie y prefijo de tópicos"],
            ["`database is locked`", "dos backends sobre la misma base", "cerrar el otro proceso"],
            ["Comandos en `TIMEOUT`", "nodo desconectado o sin suscripción", "verificar estado y `.../cmd`"],
            ["Login rechazado", "credenciales o `SECRET_KEY` cambiada", "revisar `.env` y volver a entrar"],
            ["ThingSpeak sin datos", "claves ausentes o cuota agotada", "revisar variables y contador de omitidos"],
            ["La gráfica no avanza", "SSE bloqueado por un proxy", "permitir `text/event-stream` sin búfer"],
        ],
        anchos=[4.8, 5.4, 6.4],
        pie="Problemas frecuentes y su solución.",
    )

    # ------------------------------------------------------------ 13. anexos
    manual.h1("13. Anexos")

    manual.h2("13.1 Estructura del repositorio")
    manual.codigo(
        """Parcial2_IoT_Seguridad/
  firmware/       12 modulos MicroPython + diagram.json + README_WOKWI.md
  backend/        main, config, mqtt_bridge, storage, commands, cloud, bus, cli
  backend/web/    app.py, auth.py y estaticos del panel
  sql/            schema.sql, seed.sql, consultas.sql
  scripts/        demo, emulador, diagramas, capturas, empaquetado
  tests/          314 pruebas y dobles de hardware
  docs/           manuales, diagramas (img) y capturas
  entregables/    ZIP de Wokwi, ZIP del proyecto y manifiesto"""
    )

    manual.h2("13.2 Comandos de uso frecuente")
    manual.tabla(
        ["Objetivo", "Comando"],
        [
            ["Arrancar el backend", "`python -m backend.main --seed`"],
            ["Demo completa", "`python scripts\\demo.py --reset --sembrar --sin-login`"],
            ["Ejecutar pruebas", "`python -m pytest`"],
            ["Histórico por consola", "`python -m backend.cli historico --horas 6`"],
            ["Comandos y latencias", "`python -m backend.cli comandos`"],
            ["Estadísticas", "`python -m backend.cli estadisticas`"],
            ["Regenerar diagramas", "`python scripts\\generar_diagramas.py`"],
            ["Regenerar capturas", "`python scripts\\capturar_dashboard.py`"],
            ["Empaquetar entregables", "`python scripts\\empaquetar.py`"],
        ],
        anchos=[5.0, 11.6],
        pie="Comandos habituales del proyecto.",
    )

    manual.h2("13.3 Documentos relacionados")
    manual.vinetas([
        "`README.md`: presentación del proyecto y puesta en marcha rápida.",
        "`docs/arquitectura.md`: decisiones de diseño ampliadas.",
        "`docs/flujo_datos.md`: recorrido del dato paso a paso.",
        "`docs/base_datos.md`: esquema, vistas y consultas.",
        "`docs/plataforma_nube.md`: configuración de ThingSpeak y TalkBack.",
        "`docs/instalacion.md`: instalación y publicación.",
        "`docs/guia_demo.md`: guion de la demostración y capturas.",
        "`Manual_Usuario_Centinela_IoT.docx`: guía de uso para el operador.",
    ])

    manual.parrafo()
    manual.parrafo("— Fin del manual técnico —", alineacion="centro", cursiva=True, color=GRIS)

    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
