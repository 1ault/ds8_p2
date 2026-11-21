# Cumplimiento de los requisitos — Centinela IoT

Escenario **4: Sistema de Seguridad — Detección y alertas**.
Referencia: `asignacion/Parcial_2.pdf` (Parcial #2, Desarrollo de Software VIII).

Verificación: **324 pruebas** en verde (`python -m pytest -q`).

---

## 1. Requisitos del enunciado

| # | Requisito del PDF | Cómo se cumple | Evidencia | Estado |
|---|-------------------|----------------|-----------|--------|
| 1 | **Mínimo 2 sensores diferentes** | Cuatro tipos: DHT22 (temperatura y humedad), PIR (movimiento), HC-SR04 (distancia) y LDR (luz) | `firmware/sensors.py::DhtSensor/PirSensor/UltrasonicSensor/LightSensor`; pines en `firmware/config.py:59-63` | Cumple (4) |
| 2 | **Mínimo 2 actuadores** (LEDs, buzzer, motor, relay, LCD/OLED) | Cinco: LED rojo, LED verde, sirena (buzzer PWM), servo-cerradura y OLED SSD1306 | `firmware/actuators.py::Led/Buzzer/ServoLock`; `firmware/display.py::Pantalla`; pines `config.py:64-69` | Cumple (5) |
| 3 | **Código en Python modular y bien documentado** | 12 módulos de firmware con una responsabilidad cada uno + backend en capas; docstrings, tipos en el backend y comentarios de decisión | `firmware/` (12 `.py`), `backend/` (9 módulos), `CONTRIBUTING.md` | Cumple |
| 4 | **Manejo de GPIO con librerías apropiadas** | Todo el uso de `machine`, `dht`, `network` y `framebuf` está aislado en `hal.py`; el resto inyecta los objetos | `firmware/hal.py` (`Pin`, `PWM`, `ADC`, `I2C`, `DHT22`, `pulse_us`) | Cumple |
| 5 | **Lectura de sensores en tiempo real** | Tarea asíncrona que respeta el período de cada sensor (PIR 0,15 s, distancia 0,5 s, luz 1 s, clima 5 s) sobre un reloj monotónico de milisegundos | `firmware/app.py::_bucle_sensores`; `sensors.py::SensorSuite.actualizar` | Cumple |
| 6 | **Control de actuadores** | La FSM emite efectos (`sirena_on`, `cerrar_cerradura`, …) y el controlador los aplica; sirena bitonal 2,4/2,9 kHz y LED intermitente en `ALARM` | `firmware/fsm.py` + `app.py::_aplicar` y `_bucle_leds` | Cumple |
| 7 | **Cliente MQTT en el dispositivo** (HiveMQ) | Cliente MQTT 3.1.1 propio sobre `socket`/`ssl`: CONNECT, PUBLISH QoS 0/1, PUBACK, PINGREQ, LWT `offline` y reconexión con backoff | `firmware/mqtt_client.py`; tópicos `config.py:48-54`; broker `broker.hivemq.com` | Cumple |
| 8 | **Base de datos con históricos** | SQLite con lecturas fechadas por el servidor, eventos, comandos con latencia y estado, y 12 consultas de histórico y agregación | `backend/storage.py`; `sql/schema.sql`, `sql/consultas.sql`, `sql/seed.sql`; `backend/cli.py` | Cumple |
| 9 | **Plataforma en la nube (una opción)** + dashboard + comandos desde la nube | ThingSpeak: canal de 8 campos cada 20 s y cola de comandos **TalkBack** cada 15 s, que el backend convierte en comandos MQTT | `backend/cloud.py::NubeThingSpeak`; `backend/main.py::_bucle_talkback`; `docs/plataforma_nube.md` | **Requiere claves** (ver §3) |
| 10 | **Programación modular y orientada a eventos** | Bus de eventos con buzones acotados y tareas cooperativas en el nodo; bus + cola asíncrona en el backend; panel en vivo por SSE | `firmware/bus.py`; `backend/bus.py`; `app.py::ejecutar` | Cumple |

## 2. Criterios de evaluación

| Criterio | Peso | Evidencia |
|----------|------|-----------|
| Funcionamiento completo del sistema | 30 % | Cadena completa: PIR/HC-SR04 → FSM → sirena + LEDs + OLED → MQTT → SQLite → panel → ThingSpeak. Verificada en Wokwi y en CPython con `scripts/diagnostico_pir.py` (6 escenarios) y `scripts/emular_nodo.py` |
| Calidad del código | 10 % | 12 módulos de firmware sin números mágicos (todo en `config.py`), FSM pura sin hardware, HAL inyectable, 324 pruebas (fsm 39, mqtt 45, sensors 28, app 36, cloud 24, storage 30, bridge 30, commands 29, web 20, actuators 18, display 16, auth 9) |
| Integración de todos los componentes | 5 % | `docs/img/arquitectura.png`, `docs/arquitectura.md`, `docs/flujo_datos.md`; 30 conexiones del diagrama validadas |
| Documentación | 5 % | `README.md`, `docs/` (arquitectura, flujo de datos, base de datos, plataforma en la nube, instalación, guía de demo), seis manuales en Word y PDF |
| Sustentación | 50 % | `docs/guia_demo.md` (guion de 8–10 min, preguntas frecuentes del jurado) |

## 3. Entregables

| Entregable | Estado | Dónde |
|------------|--------|-------|
| Código fuente en GitHub | Cumple | <https://github.com/1ault/ds8_p2> (release v2.0.0) |
| Código fuente en Teams | **Pendiente** (lo sube el estudiante) | — |
| `README.md` | Cumple | `README.md` |
| `requirements.txt` con lo aportado en el examen | Cumple | `aiohttp`, `paho-mqtt`, `python-dotenv`, con la justificación al inicio del archivo |
| Scripts SQL | Cumple | `sql/schema.sql`, `sql/consultas.sql`, `sql/seed.sql` |
| Diagrama de la arquitectura | Cumple | `docs/img/arquitectura.png`, `docs/arquitectura.md` |
| Diagrama de flujo de datos | Cumple | `docs/img/flujo_datos.png`, `docs/flujo_datos.md` |
| Capturas del circuito | Cumple | `docs/capturas/wokwi_01..05_*.png` |
| ZIP del proyecto Wokwi | Cumple | `Wokwi_Centinela_IoT_480810097290000385.zip` |
| Configuración de la plataforma Cloud | Documentada; **faltan las claves** | `docs/plataforma_nube.md`, `.env.example` |
| Capturas propias de ThingSpeak y TalkBack | **Pendiente** (requieren cuenta) | `docs/guia_demo.md` §4.1 |
| Sustentación oral | **Pendiente** | `docs/guia_demo.md` |

## 4. Lo que falta y cómo se cierra (10 minutos)

### 4.1 ThingSpeak (requisito 9)

1. Crear la cuenta en <https://thingspeak.com> y un canal con **8 campos**.
2. Copiar `.env.example` a `.env` y completar:

```bat
THINGSPEAK_CHANNEL=<id del canal>
THINGSPEAK_WRITE_KEY=<write api key>
THINGSPEAK_READ_KEY=<read api key>
THINGSPEAK_TALKBACK_ID=<id de la app TalkBack>
THINGSPEAK_TALKBACK_KEY=<api key de TalkBack>
```

3. Reiniciar el backend: debe registrar `ThingSpeak activo (canal ...)` y el panel
   deja de mostrar `NUBE OFF`.
4. Escribir `arm` en la cola de TalkBack: en ≤ 15 s aparece el comando con
   origen `thingspeak` y el nodo se arma.

### 4.2 Wokwi: que los cuatro sensores lean

| Sensor | Acción en el simulador |
|--------|------------------------|
| DHT22 | Nada: entrega clima desde el arranque |
| LDR | Nada (o mover el deslizador de luz) |
| **HC-SR04** | Clic en el sensor y mover el deslizador de distancia (arranca en **400 cm**, ya aceptado por el firmware desde esta sesión). Para disparar la alarma de proximidad, bajarlo a menos de 80 cm |
| **PIR** | Clic en el sensor → **Simulate Motion**. Debe hacerse **después** de que el OLED diga `ARMADO` |

### 4.3 Prueba de humo de la alarma

```bat
python scripts\diagnostico_pir.py
```

Debe terminar con `0 caso(s) con falla`. En Wokwi, con el sistema armado,
"Simulate Motion" produce en menos de un segundo: OLED `ALARMA` / `Mov SI` /
`Alerta 1` / `Sir. SIRENA`, sirena bitonal, LED rojo intermitente y la línea
`[centinela] Sirena activada` en el monitor serie.

## 5. Verificación reproducible

```bat
cd C:\Users\Usuario\code\iot_p2
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe -m pytest -q
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe scripts\diagnostico_pir.py
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe scripts\emular_nodo.py --escenario intruso --duracion 60
```

| Comprobación | Resultado esperado |
|--------------|--------------------|
| `pytest -q` | `324 passed` |
| `diagnostico_pir.py` | `0 caso(s) con falla` (6/6) |
| `emular_nodo.py --escenario intruso` | eventos `intrusion` y `alarm` publicados; el panel pasa a **ALARMA** |
| Panel web | <http://127.0.0.1:8000>, `admin` / `seguridad2026` |

## 6. Terminología usada

- **Detección**: PIR (movimiento), HC-SR04 (presencia cercana) y umbral de
  temperatura del DHT22.
- **Alerta**: cada intrusión registrada por la FSM (`alerts`), con su evento
  `intrusion` en MQTT y su fila en SQLite.
- **Alarma**: estado `ALARM` de la FSM, con sirena bitonal, LED rojo
  intermitente y aviso en el OLED (`ALARMA` / `Sir. SIRENA`).
