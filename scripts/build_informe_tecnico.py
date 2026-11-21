"""Genera el Informe Tecnico del proyecto Centinela IoT (DOCX).

Uso:
    python scripts/build_informe_tecnico.py
Salida:
    docs/manuales/Informe_Tecnico_Centinela_IoT.docx
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
SALIDA = RAIZ / "docs" / "manuales" / "Informe_Tecnico_Centinela_IoT.docx"

VERSION = "2.0.0"


def construir() -> Path:
    manual = Manual(
        titulo="Informe técnico",
        subtitulo="Desarrollo de un sistema IoT de seguridad con detección y alertas "
                  "sobre ESP32, MQTT, SQLite y ThingSpeak",
        version=VERSION,
        autor="Estudiante de Desarrollo de Software VIII",
        materia="Parcial #2 · Desarrollo de Software VIII",
        encabezado="Centinela IoT · Informe técnico",
    )

    manual.portada(
        imagen=IMG / "arquitectura.png",
        ancho_imagen_cm=15.2,
        resumen="Informe del desarrollo, la verificación y los resultados del sistema "
                "Centinela IoT, presentado como evidencia del Parcial #2 de Desarrollo "
                "de Software VIII (escenario 4: sistema de seguridad con detección y "
                "alertas).",
        metadatos=[
            ("Asignatura", "Desarrollo de Software VIII"),
            ("Evaluación", "Parcial #2 · escenario 4: sistema de seguridad"),
            ("Autor", "Estudiante de Desarrollo de Software VIII"),
            ("Versión del sistema", "v%s" % VERSION),
            ("Fecha", manual.fecha),
        ],
    )

    # ---------------------------------------------------------------- resumen
    manual.h1("Resumen", nueva_pagina=False)
    manual.parrafo("Este informe documenta el diseño, la implementación y la verificación "
                   "de **Centinela IoT**, un sistema de seguridad residencial que detecta "
                   "intrusiones y emite alertas. El sistema se compone de un nodo ESP32 "
                   "programado en MicroPython y simulado en Wokwi, un broker MQTT público, "
                   "un backend asíncrono en Python con base de datos SQLite y un panel web "
                   "en tiempo real, además de una integración con la plataforma ThingSpeak.")
    manual.parrafo("La solución cubre los requisitos del enunciado con cuatro sensores "
                   "(temperatura y humedad, movimiento, distancia y luminosidad) y cinco "
                   "actuadores (dos LEDs, sirena, cerradura con servo y pantalla OLED). La "
                   "lógica de seguridad se implementó como una máquina de estados pura, "
                   "aislada del hardware, lo que permitió verificarla con pruebas "
                   "automatizadas. El protocolo MQTT se implementó desde cero sobre asyncio, "
                   "porque no existen clientes disponibles para MicroPython en el entorno "
                   "simulado.")
    manual.parrafo("El sistema se validó con **324 pruebas automatizadas** (todas "
                   "aprobadas), una demostración de extremo a extremo con broker real y una "
                   "captura automatizada del simulador. La telemetría real confirmó la "
                   "secuencia de estados `ARMING → ARMED → ALARM` con sirena activa. El "
                   "proceso dejó además tres hallazgos documentados sobre el comportamiento "
                   "del simulador y del hardware, que se discuten en el apartado 7.")
    manual.parrafo("**Palabras clave:** Internet de las cosas, seguridad residencial, MQTT, "
                   "MicroPython, ESP32, SQLite, ThingSpeak, sistemas orientados a eventos.")

    manual.h2("Ficha del informe")
    manual.bloque_datos([
        ("Tipo de trabajo", "desarrollo e implementación de un sistema IoT completo"),
        ("Escenario", "4 — sistema de seguridad con detección y alertas"),
        ("Alcance", "dispositivo, transporte, servicios, panel, nube y documentación"),
        ("Tecnologías", "ESP32 y MicroPython, MQTT, Python con aiohttp, SQLite, ThingSpeak"),
        ("Verificación", "324 pruebas automatizadas, demostración de extremo a extremo y "
                         "capturas del simulador"),
        ("Entregables", "este informe, manual técnico, manual del usuario, paquete del "
                        "proyecto y proyecto de Wokwi"),
    ])

    # ------------------------------------------------------------------ indice
    manual.h1("Contenido")
    manual.tabla(
        ["Sección", "Contenido"],
        [
            ["1. Introducción", "contexto, problema, justificación y alcance"],
            ["2. Objetivos", "objetivo general y objetivos específicos"],
            ["3. Marco teórico", "IoT, MQTT, MicroPython, persistencia y nube"],
            ["4. Metodología", "fases, herramientas y estrategia de verificación"],
            ["5. Desarrollo de la solución", "arquitectura, firmware, servicios y panel"],
            ["6. Resultados", "pruebas, verificación en simulador y métricas"],
            ["7. Discusión", "hallazgos, limitaciones y comparación de alternativas"],
            ["8. Conclusiones", "cierre de los objetivos planteados"],
            ["9. Recomendaciones", "mejoras y trabajo futuro"],
            ["10. Referencias", "fuentes en formato APA 7"],
            ["Anexos", "repositorio, evidencias y comandos de reproducción"],
        ],
        anchos=[4.6, 12.0],
        pie="Estructura del informe.",
    )

    # ------------------------------------------------------------ 1. intro
    manual.h1("1. Introducción")

    manual.h2("1.1 Contexto y problema")
    manual.parrafo("La seguridad de una vivienda suele resolverse con equipos comerciales "
                   "cerrados: el usuario no puede auditar qué ocurrió, los datos quedan en "
                   "servidores ajenos y añadir un sensor implica cambiar de sistema. Al mismo "
                   "tiempo, las plataformas de Internet de las cosas permiten construir "
                   "soluciones a medida con componentes de bajo costo y servicios gratuitos.")
    manual.parrafo("El problema abordado en este trabajo es concreto: **detectar la presencia "
                   "de una persona en un acceso y avisar de forma inequívoca**, dejando "
                   "registro de lo ocurrido y permitiendo operar el sistema a distancia, con "
                   "material de bajo costo y sin depender por completo de la nube.")

    manual.h2("1.2 Justificación")
    manual.parrafo("Se eligió el escenario 4 (sistema de seguridad con detección y alertas) "
                   "porque exige integrar casi todos los componentes de un sistema IoT real: "
                   "adquisición de datos, decisión local, actuación, comunicación "
                   "bidireccional, persistencia histórica y presentación al usuario. Además, "
                   "permite demostrar dos aspectos que suelen quedar fuera de los ejercicios "
                   "introductorios: la **auditoría de comandos** con confirmación y la "
                   "**degradación controlada** cuando falla la red o la nube.")

    manual.h2("1.3 Alcance y delimitación")
    manual.parrafo("El alcance incluye el dispositivo, el transporte, los servicios y la "
                   "interfaz de operación, junto con su documentación. Quedan fuera del "
                   "alcance la integración con cerraduras certificadas, el aprovisionamiento "
                   "masivo de dispositivos, la gestión multipropietario y el análisis "
                   "predictivo de datos. El sistema se valida en simulación y con pruebas "
                   "automatizadas; no se realizó un despliegue físico permanente.")

    # --------------------------------------------------------- 2. objetivos
    manual.h1("2. Objetivos")

    manual.h2("2.1 Objetivo general")
    manual.parrafo("Diseñar e implementar un sistema IoT de seguridad que detecte "
                   "intrusiones, emita alertas locales y remotas, registre el histórico con "
                   "marca de tiempo y permita el control bidireccional desde una interfaz "
                   "web y desde la nube.")

    manual.h2("2.2 Objetivos específicos")
    manual.numerada([
        "Construir un nodo con al menos cuatro sensores y cinco actuadores, con lectura en "
        "tiempo real y control mediante librerías apropiadas de GPIO.",
        "Implementar una máquina de estados de seguridad que determine cuándo alertar, con "
        "reglas explícitas y verificables.",
        "Desarrollar un cliente MQTT en el dispositivo con QoS 0 y 1, Last Will y "
        "reconexión automática.",
        "Almacenar lecturas, eventos y comandos en una base de datos con marca de tiempo "
        "del servidor y consultas de históricos.",
        "Publicar los datos en una plataforma en la nube y recibir comandos desde ella.",
        "Ofrecer un panel en tiempo real con autenticación, control remoto y auditoría.",
        "Verificar el conjunto con pruebas automatizadas y una demostración de extremo a "
        "extremo.",
    ])

    # ------------------------------------------------------- 3. marco teorico
    manual.h1("3. Marco teórico")

    manual.h2("3.1 Internet de las cosas en seguridad residencial")
    manual.parrafo("Un sistema IoT se organiza habitualmente en cuatro capas: percepción, "
                   "red, procesamiento y aplicación. En seguridad residencial, la capa de "
                   "percepción combina sensores discretos (movimiento, apertura) con sensores "
                   "analógicos (temperatura, luz) y la capa de aplicación debe garantizar que "
                   "una detección se traduzca en una alerta perceptible, incluso si la red "
                   "falla. Ese requisito es el que justifica que la decisión crítica viva en "
                   "el propio dispositivo y no solo en el servidor.")

    manual.h2("3.2 MQTT")
    manual.parrafo("MQTT es un protocolo de publicación y suscripción sobre TCP, pensado "
                   "para enlaces inestables y dispositivos con recursos limitados. Define "
                   "tres niveles de calidad de servicio: **QoS 0** (sin confirmación), "
                   "**QoS 1** (al menos una entrega) y **QoS 2** (exactamente una). Incluye "
                   "además el mecanismo *Last Will and Testament*, que permite al broker "
                   "anunciar la caída de un cliente, y la retención de mensajes de estado "
                   "(OASIS, 2014; HiveMQ, 2024).")

    manual.h2("3.3 ESP32, MicroPython y simulación")
    manual.parrafo("El ESP32 integra Wi-Fi y Bluetooth, convertidores analógico-digitales y "
                   "periféricos PWM, lo que lo hace adecuado para nodos de bajo costo "
                   "(Espressif Systems, 2024). MicroPython ofrece un subconjunto de Python 3 "
                   "sobre el microcontrolador, con acceso a GPIO mediante el módulo `machine` "
                   "y concurrencia cooperativa con `asyncio` (MicroPython, 2024). Wokwi "
                   "permite simular la placa y sus módulos en el navegador, con salida real a "
                   "Internet a través de su red virtual (Wokwi, 2024).")

    manual.h2("3.4 Persistencia y plataformas en la nube")
    manual.parrafo("SQLite es un motor embebido que no requiere servidor y que, en modo WAL, "
                   "admite lecturas concurrentes con una escritura (SQLite, 2024). Para la "
                   "capa de nube se eligió ThingSpeak, que ofrece canales de ocho campos con "
                   "gráficas y una aplicación de cola de comandos (*TalkBack*) accesible por "
                   "API REST (The MathWorks, 2024).")

    # -------------------------------------------------------- 4. metodologia
    manual.h1("4. Metodología")

    manual.h2("4.1 Enfoque y fases")
    manual.parrafo("Se aplicó un enfoque de construcción incremental con verificación "
                   "continua, inspirado en el ciclo de vida en espiral: cada fase terminaba "
                   "con pruebas ejecutables antes de pasar a la siguiente.")
    manual.tabla(
        ["Fase", "Actividades", "Producto verificable"],
        [
            ["1. Análisis", "lectura del enunciado, requisitos y escenario",
             "lista de requisitos y checklist"],
            ["2. Diseño", "arquitectura de capas, contrato MQTT y modelo de datos",
             "diagramas y tablas de contrato"],
            ["3. Construcción del firmware", "HAL, sensores, FSM, cliente MQTT, controlador",
             "pruebas de firmware en CPython"],
            ["4. Construcción de servicios", "almacén, comandos, nube, API y panel",
             "pruebas de backend y de API"],
            ["5. Integración", "broker real, nodo emulado y simulador",
             "demostración de extremo a extremo"],
            ["6. Documentación", "manuales, diagramas y capturas",
             "documentos y paquete de entrega"],
        ],
        anchos=[4.0, 7.4, 5.2],
        pie="Fases del proyecto y su producto verificable.",
    )

    manual.h2("4.2 Herramientas")
    manual.tabla(
        ["Herramienta", "Uso en el proyecto"],
        [
            ["Wokwi", "simulación del ESP32 y de los diez módulos del circuito"],
            ["MicroPython", "lenguaje del firmware, con `asyncio` y `machine`"],
            ["Python 3.15 + aiohttp", "backend asíncrono, API REST y SSE"],
            ["paho-mqtt", "cliente MQTT del backend, adaptado a asyncio"],
            ["SQLite", "histórico, eventos, comandos y transiciones"],
            ["ThingSpeak", "canal de ocho campos y cola de comandos TalkBack"],
            ["pytest + pytest-asyncio", "324 pruebas automatizadas"],
            ["Pillow", "generación de diagramas y capturas de consola"],
            ["Chrome headless + DevTools", "capturas reales del panel y del simulador"],
        ],
        anchos=[5.0, 11.6],
        pie="Herramientas utilizadas.",
    )

    manual.h2("4.3 Estrategia de verificación")
    manual.parrafo("La verificación se organizó en tres niveles. El **nivel unitario** prueba "
                   "la lógica pura (máquina de estados, codificación de paquetes, validación "
                   "de comandos) sin hardware. El **nivel de integración** enfrenta el cliente "
                   "MQTT a un broker falso que habla TCP real, el backend a una base SQLite "
                   "real y la API a un servidor de pruebas. El **nivel de sistema** ejecuta la "
                   "demostración completa con broker público y un nodo emulado que reutiliza "
                   "el código real del firmware.")
    manual.parrafo("Para que el firmware fuera verificable en un computador, todo el acceso al "
                   "hardware se aisló en un único módulo (`hal.py`) y se sustituyó por dobles "
                   "en las pruebas. Esta decisión, tomada en la fase de diseño, fue la que "
                   "hizo posible el nivel de cobertura alcanzado.")

    manual.h2("4.4 Instrumentos de evidencia")
    manual.vinetas([
        "Reporte de pruebas con conteo por archivo y resultado final.",
        "Capturas reales del panel, del login y de las consultas de consola.",
        "Capturas del simulador: circuito, monitor serie y pantalla en dos estados.",
        "Telemetría real recibida por MQTT durante la demostración de extremo a extremo.",
        "Manifiesto con tamaño y SHA-256 de cada archivo entregado.",
    ])

    # ---------------------------------------------------------- 5. desarrollo
    manual.h1("5. Desarrollo de la solución")

    manual.h2("5.1 Arquitectura general")
    manual.parrafo("La solución se organiza en cuatro capas con responsabilidades separadas. "
                   "La decisión más relevante fue interponer un backend entre el dispositivo y "
                   "la nube: SQLite no cabe en el microcontrolador, los comandos requieren "
                   "validación y auditoría, y el panel debe seguir siendo útil si la nube "
                   "falla.")
    manual.figura(IMG / "arquitectura.png",
                  "Arquitectura de cuatro capas del sistema.", ancho_cm=15.6)

    manual.h2("5.2 Nodo de adquisición y control")
    manual.parrafo("El nodo se implementó en doce módulos con una responsabilidad cada uno. "
                   "La lógica de seguridad es una máquina de estados de cuatro estados que "
                   "devuelve **efectos** en lugar de accionar hardware, lo que la hace "
                   "verificable de forma aislada.")
    manual.figura(IMG / "fsm.png",
                  "Máquina de estados de seguridad con sus transiciones y notas.",
                  ancho_cm=14.8)
    manual.tabla(
        ["Métrica del firmware", "Valor"],
        [
            ["Módulos", "12 archivos Python"],
            ["Líneas de código", "2 430"],
            ["Tareas asíncronas", "7 (MQTT, sensores, telemetría, LEDs, pantalla, comandos, botón)"],
            ["Sensores / actuadores", "4 / 5"],
            ["Pruebas del firmware", "156 casos en 6 archivos"],
        ],
        anchos=[6.4, 10.2],
        pie="Dimensiones del subsistema de dispositivo.",
    )

    manual.h2("5.3 Protocolo de comunicación")
    manual.parrafo("Se definieron seis tópicos con QoS diferenciado por criticidad: "
                   "telemetría en QoS 0 porque una lectura perdida se recupera con la "
                   "siguiente; eventos, comandos y confirmaciones en QoS 1 porque perderlos "
                   "cambia el estado del sistema. El estado del nodo se publica retenido para "
                   "que un panel que se conecte tarde conozca la situación vigente.")
    manual.tabla(
        ["Tópico", "QoS", "Función"],
        [
            ["`.../telemetry`", "0", "lecturas de los cuatro sensores cada 5 s"],
            ["`.../events`", "1", "alarmas, cambios de estado y avisos de red"],
            ["`.../status`", "1 ret.", "`online` / `offline` mediante Last Will"],
            ["`.../cmd`", "1", "comandos desde el panel o desde la nube"],
            ["`.../ack`", "1", "confirmación con resultado y motivo"],
            ["`.../config`", "1", "cambio de umbrales en caliente"],
        ],
        anchos=[4.4, 2.2, 10.0],
        alinear_centro=(1,),
        pie="Contrato de tópicos del sistema.",
    )
    manual.parrafo("El cliente MQTT se escribió sobre `asyncio.open_connection` porque no "
                   "existen bibliotecas MQTT para MicroPython en el entorno simulado. La mitad "
                   "del módulo son funciones puras de codificación de paquetes, verificadas "
                   "byte a byte con 45 casos de prueba.")

    manual.h2("5.4 Servicios y persistencia")
    manual.parrafo("El backend ejecuta un bucle de eventos único. paho-mqtt trabaja en un hilo "
                   "propio y sus callbacks alimentan una cola asíncrona, de modo que el resto "
                   "del sistema no ve hilos. Las escrituras en SQLite se serializan con un "
                   "lock y se ejecutan en un hilo aparte, con WAL activo.")
    manual.figura(IMG / "modelo_datos.png",
                  "Modelo de datos: cinco tablas, claves foráneas y cardinalidad.",
                  ancho_cm=15.0)
    manual.tabla(
        ["Métrica del backend", "Valor"],
        [
            ["Módulos", "10 archivos Python (más el paquete web)"],
            ["Líneas de código", "2 273"],
            ["Interfaz del panel", "1 155 líneas de HTML, CSS y JavaScript"],
            ["Base de datos", "5 tablas, 5 vistas, 7 índices, 12 consultas"],
            ["Pruebas del backend", "158 casos en 6 archivos"],
        ],
        anchos=[6.4, 10.2],
        pie="Dimensiones del subsistema de servicios.",
    )
    manual.parrafo("El servicio de comandos es la pieza central de la auditabilidad: valida "
                   "el comando, lo registra antes de publicarlo, espera la confirmación con "
                   "tiempo límite y cierra el ciclo como `OK`, `RECHAZADO`, `TIMEOUT` o "
                   "`ERROR`, guardando la latencia medida.")

    manual.h2("5.5 Interfaz de operación")
    manual.parrafo("El panel se construyó con aiohttp y Server-Sent Events. Se descartó "
                   "WebSocket porque el flujo es de un solo sentido, SSE ofrece reconexión "
                   "nativa del navegador y no añade dependencias. La sesión es una cookie "
                   "firmada con HMAC-SHA256 y la comparación de credenciales usa tiempo "
                   "constante.")
    manual.figura(CAP / "02_panel_alarma.png",
                  "Panel del operador durante una alarma, con eventos y auditoría de comandos.",
                  ancho_cm=16.0)

    manual.h2("5.6 Integración con la nube")
    manual.parrafo("ThingSpeak recibe una lectura cada 20 segundos en un canal de ocho campos "
                   "y devuelve comandos mediante TalkBack cada 15 segundos. La integración se "
                   "implementó como un servicio sustituible: sin claves configuradas, el "
                   "sistema usa una implementación nula y funciona íntegramente en local.")

    manual.h2("5.7 Decisiones de diseño y su justificación")
    manual.tabla(
        ["Decisión", "Alternativa descartada", "Motivo"],
        [
            ["Backend intermedio", "ESP32 → ThingSpeak directo",
             "histórico local, validación y auditoría de comandos"],
            ["Cliente MQTT propio", "biblioteca existente",
             "no hay cliente MQTT para MicroPython en el simulador"],
            ["asyncio en todo el sistema", "hilos y servidor bloqueante",
             "un solo modelo de concurrencia y tareas cancelables"],
            ["SQLite con un escritor", "MySQL o PostgreSQL",
             "instalación nula y suficiente para un nodo"],
            ["SSE", "WebSocket",
             "flujo unidireccional, reconexión nativa y cero dependencias"],
            ["Máquina de estados pura", "condicionales dispersos",
             "verificabilidad y trazabilidad de las reglas"],
            ["Marcas de tiempo del servidor", "reloj del dispositivo",
             "el nodo no tiene RTC y un reinicio rompería el histórico"],
        ],
        anchos=[4.4, 4.8, 7.4],
        pie="Decisiones de diseño y alternativas consideradas.",
    )

    # ----------------------------------------------------------- 6. resultados
    manual.h1("6. Resultados")

    manual.h2("6.1 Pruebas automatizadas")
    manual.parrafo("Se ejecutaron **324 pruebas** en CPython, con un tiempo total de "
                   "alrededor de un minuto y un resultado de 324 aprobadas y 0 fallidas. La "
                   "mayor cantidad de pruebas corresponde al firmware (156) y al protocolo "
                   "MQTT (45), que es donde se concentra el riesgo del sistema.")
    manual.tabla(
        ["Archivo de pruebas", "Casos", "Nivel"],
        [
            ["`test_fsm.py`", "39", "unitario (lógica pura)"],
            ["`test_mqtt.py`", "45", "unitario + integración con broker falso"],
            ["`test_app.py`", "28", "integración del controlador"],
            ["`test_sensors.py`", "26", "unitario con dobles de hardware"],
            ["`test_actuators.py`", "18", "unitario con dobles de hardware"],
            ["`test_display.py`", "16", "unitario de la interfaz local"],
            ["`test_storage.py`", "30", "integración con SQLite real"],
            ["`test_commands.py`", "29", "integración del servicio de comandos"],
            ["`test_bridge.py`", "30", "unitario del puente y del bus"],
            ["`test_cloud.py`", "24", "unitario con sesión HTTP falsa"],
            ["`test_web.py`", "20", "integración con servidor aiohttp"],
            ["`test_auth.py`", "9", "unitario de seguridad de sesión"],
        ],
        anchos=[4.8, 1.8, 9.8],
        alinear_centro=(1,),
        pie="Distribución de las 324 pruebas por archivo y nivel.",
    )

    manual.h2("6.2 Verificación del dispositivo en el simulador")
    manual.parrafo("El firmware se cargó en el simulador y arrancó sin errores. El monitor "
                   "serie confirmó la secuencia de inicialización completa: pantalla, WiFi y "
                   "conexión al broker. El nodo se conectó a la red virtual, obtuvo dirección "
                   "y estableció la sesión MQTT.")
    manual.figura(CAP / "wokwi_02_serie.png",
                  "Monitor serie del nodo en el simulador: arranque, pantalla, WiFi y MQTT.",
                  ancho_cm=15.2)
    manual.figura(CAP / "wokwi_03_oled_armado.png",
                  "Pantalla del nodo en estado ARMADO con las lecturas de los sensores.",
                  ancho_cm=8.8)

    manual.h2("6.3 Integración de extremo a extremo")
    manual.parrafo("La demostración con broker público permitió comprobar el camino completo: "
                   "el nodo publicó telemetría que el backend almacenó, y un comando enviado "
                   "desde el servicio fue ejecutado y confirmado por el dispositivo. La "
                   "telemetría recibida durante la captura evidencia la transición de estados "
                   "y el accionamiento de la sirena.")
    manual.tabla(
        ["Variable observada", "Valor registrado", "Interpretación"],
        [
            ["Secuencia de estados", "`ARMING → ARMED → ALARM`", "la FSM respondió a los eventos"],
            ["`siren`", "`true`", "la sirena se activó en la alarma"],
            ["`alerts`", "`1`", "se contabilizó una alerta"],
            ["`temp_c` / `hum_pct`", "26.0 / 55.0", "lecturas coherentes del DHT22"],
            ["`lux`", "119.9", "conversión del LDR en rango esperado"],
            ["`rssi`", "-87 dBm", "enlace WiFi del simulador"],
            ["Confirmación del comando", "`ok = true`", "ACK recibido y auditado"],
            ["Latencia de comandos", "4 a 550 ms", "según origen (panel, nube o semilla)"],
        ],
        anchos=[4.4, 4.6, 7.6],
        pie="Evidencia de la integración de extremo a extremo.",
    )
    manual.parrafo("En la demostración local, con nodo emulado y datos sembrados, se "
                   "registraron entre 7 y 9 lecturas en 45 segundos (coherente con el periodo "
                   "de 5 s y el tiempo de simulación efectivo), 11 eventos y un comando "
                   "confirmado.")

    manual.h2("6.4 Operación del panel y auditoría")
    manual.parrafo("El panel mostró el estado, las magnitudes, la gráfica y el feed de "
                   "eventos actualizados en vivo. La tabla de comandos permitió verificar la "
                   "auditoría completa, incluidos comandos rechazados y expirados, que es el "
                   "aspecto que distingue este trabajo de una demostración elemental.")
    manual.figura(CAP / "01_panel_estado.png",
                  "Panel en operación normal, con histórico, eventos y estado del sistema.",
                  ancho_cm=15.8)
    manual.figura(CAP / "07_cli_comandos.png",
                  "Auditoría de comandos desde la consola: estado, origen y latencia.",
                  ancho_cm=15.0)

    manual.h2("6.5 Cumplimiento de requisitos")
    manual.tabla(
        ["Requisito del enunciado", "Resultado"],
        [
            ["Mínimo dos sensores", "4 implementados y verificados"],
            ["Mínimo dos actuadores", "5 implementados y verificados"],
            ["Código Python modular y documentado", "22 módulos con docstrings"],
            ["Manejo de GPIO con librerías apropiadas", "`machine` aislado en `hal.py`"],
            ["Cliente MQTT en el dispositivo", "implementado desde cero con QoS 0/1 y LWT"],
            ["Base de datos con histórico y timestamp", "SQLite, 5 tablas, 5 vistas"],
            ["Registro de eventos y comandos", "tablas `events` y `commands` con ACK"],
            ["Consultas de históricos", "12 consultas + CLI + API"],
            ["Plataforma en la nube", "ThingSpeak con 8 campos y TalkBack"],
            ["Panel en tiempo real", "aiohttp + SSE con autenticación"],
            ["Comandos desde la nube", "TalkBack → MQTT → nodo → ACK"],
            ["Programación modular orientada a eventos", "bus de eventos y tareas asíncronas"],
        ],
        anchos=[7.6, 9.0],
        pie="Cumplimiento de los requisitos del enunciado.",
    )

    manual.h2("6.6 Métricas del sistema")
    manual.tabla(
        ["Indicador", "Valor"],
        [
            ["Líneas de código del sistema", "5 858 (firmware, backend y panel)"],
            ["Líneas de pruebas", "3 353"],
            ["Relación pruebas / código", "0,57"],
            ["Cobertura funcional de la lógica crítica", "máquina de estados y protocolo al 100 % de casos previstos"],
            ["Almacenamiento estimado", "≈ 17 000 filas y 1,5 MB al mes por nodo"],
            ["Tiempo de arranque del backend", "menos de 2 segundos en local"],
        ],
        anchos=[6.8, 9.8],
        pie="Indicadores cuantitativos del proyecto.",
    )

    # ------------------------------------------------------------- 7. discusion
    manual.h1("7. Discusión")

    manual.h2("7.1 Hallazgos técnicos")
    manual.parrafo("El proceso de verificación encontró defectos que no eran visibles en la "
                   "lectura del código. Se corregieron y cada uno quedó cubierto por una "
                   "prueba, lo que evita su reaparición:")
    manual.tabla(
        ["Hallazgo", "Impacto", "Corrección"],
        [
            ["Divisor del LDR invertido", "lux altos en oscuridad",
             "modelo corregido y cubierto por pruebas de monotonía"],
            ["`UPDATE` con `lastrowid`", "confirmación de comando siempre exitosa",
             "se devuelve el número de filas afectadas"],
            ["Clave foránea sin dispositivo", "fallo al registrar comandos",
             "aseguramiento previo del dispositivo"],
            ["Payload crudo en el bus de comandos", "comandos no procesados",
             "publicación del evento en el bus y prueba de integración"],
            ["Cierre de socket bloqueante", "el cliente MQTT no terminaba",
             "cierre explícito del transporte antes de esperar"],
            ["Numeración de la pantalla", "texto tapado por el bisel",
             "contenido reubicado en la pantalla"],
        ],
        anchos=[5.2, 5.4, 6.0],
        pie="Defectos detectados durante la verificación y su corrección.",
    )

    manual.h2("7.2 Limitaciones observadas")
    manual.vinetas([
        "**Distancia en simulación**: la lectura del sensor ultrasónico no siempre entrega "
        "valores en el simulador, por lo que la detección por proximidad no pudo validarse "
        "allí; la lógica asociada sí está cubierta por pruebas unitarias.",
        "**Entrada de movimiento en navegador headless**: el botón de simulación del sensor "
        "PIR no siempre llega al firmware cuando la simulación corre sin interfaz visible. "
        "La alarma se verificó mediante un comando de configuración enviado desde la nube, "
        "que es un camino legítimo del sistema.",
        "**Broker público**: el entorno de prácticas no exige autenticación, de modo que "
        "cualquier cliente podría publicar en los tópicos. El sistema contempla TLS y "
        "credenciales, pero no se activaron en la demostración.",
        "**Sin despliegue físico**: la validación se hizo en simulación y con pruebas "
        "automatizadas; no se midió el consumo eléctrico ni la resistencia de la cerradura "
        "en campo.",
    ])

    manual.h2("7.3 Comparación con alternativas")
    manual.parrafo("Frente a una solución comercial, este sistema sacrifica acabado y "
                   "certificación a cambio de auditabilidad total, costo casi nulo y "
                   "posibilidad de modificar cualquier regla. Frente a una solución "
                   "académica mínima (sensor, LED y una plataforma), añade persistencia "
                   "propia, auditoría de comandos, degradación controlada y una batería de "
                   "pruebas, que son precisamente los criterios de evaluación del trabajo.")

    # ---------------------------------------------------------- 8. conclusiones
    manual.h1("8. Conclusiones")

    manual.parrafo("El objetivo general se cumplió: el sistema detecta intrusiones, emite "
                   "alertas locales y remotas, conserva el histórico con marca de tiempo y "
                   "admite control bidireccional desde el panel y desde la nube.")
    manual.parrafo("Los objetivos específicos se alcanzaron con evidencia verificable: los "
                   "cuatro sensores y cinco actuadores funcionan y están documentados; la "
                   "máquina de estados concentra las reglas de seguridad y se prueba de forma "
                   "aislada; el cliente MQTT propio cubre QoS 0 y 1 con Last Will y "
                   "reconexión; la base de datos conserva lecturas, eventos y comandos con sus "
                   "doce consultas de históricos; ThingSpeak recibe los datos y entrega "
                   "comandos; el panel opera en tiempo real con autenticación; y las 324 "
                   "pruebas se ejecutan sin fallos.")
    manual.parrafo("La enseñanza principal del proyecto es que **la verificabilidad no se "
                   "improvisa al final**: aislar el hardware en una capa, separar la lógica de "
                   "los efectos y fijar un contrato de mensajes antes de escribir código fueron "
                   "las decisiones que permitieron probar un sistema embebido sin placas y "
                   "detectar defectos que la revisión manual no había encontrado.")

    manual.h2("8.1 Aportes del trabajo")
    manual.vinetas([
        "Un contrato de comunicación explícito y versionado, que permite sustituir el nodo, "
        "el backend o la nube sin reescribir el resto del sistema.",
        "Una máquina de estados de seguridad separada del hardware, con reglas legibles y "
        "verificables, en lugar de condicionales repartidos por el código.",
        "Un esquema de auditoría de comandos que registra origen, resultado y latencia, y que "
        "distingue entre rechazo, error y expiración.",
        "Un conjunto de 324 pruebas que cubre desde la codificación de paquetes MQTT hasta la "
        "API del panel, ejecutable en un computador sin hardware.",
        "Un proceso reproducible de evidencias: diagramas, capturas del panel y del "
        "simulador, y manifiesto con verificación de integridad.",
    ])

    manual.h2("8.2 Reflexión sobre el proceso")
    manual.parrafo("El mayor costo del proyecto no estuvo en escribir el sistema, sino en "
                   "comprobar que hacía lo que decía hacer. Las pruebas encontraron defectos "
                   "silenciosos —una fórmula de luminosidad invertida, una confirmación de "
                   "comandos que siempre resultaba exitosa, un cierre de conexión que se "
                   "bloqueaba— que no producían errores visibles pero invalidaban parte de la "
                   "lógica. Ese hallazgo refuerza una idea sencilla: en sistemas de seguridad, "
                   "lo que no está verificado no puede considerarse terminado.")

    # ------------------------------------------------------- 9. recomendaciones
    manual.h1("9. Recomendaciones y trabajo futuro")

    manual.numerada([
        "Instrumentar el nodo real para medir consumo y tiempo de respuesta de la cerradura "
        "en condiciones de campo.",
        "Migrar a un broker con autenticación y TLS por defecto, con credenciales por "
        "dispositivo.",
        "Añadir una segunda fuente de detección (sensor de apertura de puerta) para reducir "
        "falsos negativos ante un PIR bloqueado.",
        "Incorporar notificaciones push o correo ante eventos críticos, con confirmación de "
        "lectura por parte del operador.",
        "Sustituir la verificación de distancia pendiente por una calibración del sensor "
        "ultrasónico y pruebas de campo con distintos materiales.",
        "Añadir retención por agregados (promedios horarios) para reducir el crecimiento del "
        "histórico a largo plazo.",
        "Automatizar la captura de evidencias en el proceso de integración continua, de modo "
        "que cada versión genere sus propias imágenes y su reporte.",
    ])

    # ---------------------------------------------------------- 10. referencias
    manual.h1("10. Referencias")
    manual.parrafo("Las referencias siguen el formato APA, séptima edición.")
    for referencia in [
        "aiohttp contributors. (2024). *aiohttp documentation* (versión 3.14). "
        "https://docs.aiohttp.org/",
        "Eclipse Foundation. (2024). *Eclipse Paho MQTT client documentation*. "
        "https://eclipse.dev/paho/",
        "Espressif Systems. (2024). *ESP32 series datasheet* (versión 4.x). "
        "https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf",
        "Fielding, R. T. (2000). *Architectural styles and the design of network-based "
        "software architectures* [Tesis doctoral, University of California, Irvine]. "
        "https://www.ics.uci.edu/~fielding/pubs/dissertation/",
        "HiveMQ. (2024). *MQTT essentials: A lightweight messaging protocol for the "
        "Internet of Things*. https://www.hivemq.com/mqtt-essentials/",
        "International Organization for Standardization. (2011). *ISO/IEC 25010: Systems and "
        "software engineering — Systems and software Quality Requirements and Evaluation "
        "(SQuaRE) — System and software quality models*.",
        "MicroPython. (2024). *MicroPython documentation* (versión 1.2x). "
        "https://docs.micropython.org/",
        "OASIS. (2014). *MQTT version 3.1.1: OASIS standard*. "
        "http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/",
        "Pressman, R. S., y Maxim, B. R. (2020). *Ingeniería del software: un enfoque "
        "práctico* (9.ª ed.). McGraw-Hill.",
        "Sommerville, I. (2016). *Software engineering* (10.ª ed.). Pearson.",
        "SQLite. (2024). *SQLite documentation*. https://www.sqlite.org/docs.html",
        "The MathWorks. (2024). *ThingSpeak documentation*. "
        "https://www.mathworks.com/help/thingspeak/",
        "Wokwi. (2024). *Wokwi documentation: ESP32 and MicroPython*. "
        "https://docs.wokwi.com/",
    ]:
        manual.referencia(referencia)

    # ---------------------------------------------------------------- anexos
    manual.h1("Anexos")

    manual.h2("Anexo A. Estructura del repositorio")
    manual.codigo(
        """Parcial2_IoT_Seguridad/
  firmware/       12 modulos MicroPython, diagram.json y README de Wokwi
  backend/        servicios asincronos (10 modulos) y paquete web
  sql/            schema.sql, seed.sql, consultas.sql (12 consultas)
  scripts/        demo, emulador, diagramas, capturas, informes y empaquetado
  tests/          324 pruebas y dobles de hardware
  docs/           manuales (3 documentos), diagramas (img) y capturas
  entregables/    paquetes ZIP, documentos finales y manifiesto con SHA-256"""
    )

    manual.h2("Anexo B. Índice de evidencias")
    manual.tabla(
        ["Evidencia", "Archivo"],
        [
            ["Panel en operación normal", "`docs/capturas/01_panel_estado.png`"],
            ["Panel en alarma", "`docs/capturas/02_panel_alarma.png`"],
            ["Acceso al panel", "`docs/capturas/03_login.png`"],
            ["Histórico por consola", "`docs/capturas/04_cli_historico.png`"],
            ["Eventos del sistema", "`docs/capturas/05_cli_eventos.png`"],
            ["Estadísticas", "`docs/capturas/06_cli_estadisticas.png`"],
            ["Auditoría de comandos", "`docs/capturas/07_cli_comandos.png`"],
            ["Circuito en el simulador", "`docs/capturas/wokwi_01_circuito.png`"],
            ["Monitor serie del nodo", "`docs/capturas/wokwi_02_serie.png`"],
            ["Pantalla del nodo en ARMADO", "`docs/capturas/wokwi_03_oled_armado.png`"],
            ["Pantalla del nodo en ALARMA", "`docs/capturas/wokwi_04_oled_alarma.png`"],
            ["Circuito en alarma", "`docs/capturas/wokwi_05_circuito_alarma.png`"],
        ],
        anchos=[7.0, 9.6],
        pie="Evidencias incluidas en el paquete de entrega.",
    )

    manual.h2("Anexo C. Comandos de reproducción")
    manual.codigo(
        """python -m pytest                          # 324 pruebas
python -m backend.main --seed              # backend + panel
python scripts\\demo.py --reset --sembrar   # demo completa con nodo emulado
python scripts\\capturar_dashboard.py        # capturas del panel y de la consola
python scripts\\empaquetar.py                # paquetes y manifiesto"""
    )

    manual.parrafo()
    manual.parrafo("— Fin del informe técnico —", alineacion="centro", cursiva=True,
                   color=GRIS)

    return manual.guardar(SALIDA)


if __name__ == "__main__":
    ruta = construir()
    print("generado:", ruta)
