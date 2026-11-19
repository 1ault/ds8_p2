# Guía de demostración y evidencias

Guion para presentar el parcial en 8–10 minutos y lista de capturas que debe
tomar el estudiante con su propia cuenta.

---

## 1. Preparación (5 minutos antes)

```bat
cd Parcial2_IoT_Seguridad
.venv\Scripts\activate
python scripts\demo.py --reset --sembrar --sin-login --puerto 8010
```

Deja el panel en <http://127.0.0.1:8010> con 24 h de histórico y un nodo
emulado en marcha. Ten también abiertas:

- <https://wokwi.com> con el proyecto importado y **Play** pulsado.
- El canal de ThingSpeak (si está configurado).

Plan B sin Internet: añadir `--sin-mqtt` al comando anterior. El nodo y el
backend se comunican en memoria y todo lo demás funciona igual.

---

## 2. Guion de la demostración

| Tiempo | Qué mostrar | Qué decir |
|--------|-------------|-----------|
| 0:00 | Diagrama de arquitectura | "Cuatro capas: ESP32, broker MQTT, backend Python y nube/dashboard" |
| 0:45 | Circuito en Wokwi | "Cuatro sensores y cinco actuadores sobre un ESP32 con MicroPython" |
| 1:30 | Monitor serie del nodo | "Se conecta a Wokwi-GUEST, publica telemetría cada 5 s y escucha comandos" |
| 2:15 | Panel en DESARMADO | "KPIs, gráfica y eventos en tiempo real por SSE" |
| 3:00 | Pulsar **Armar** | "Cuenta regresiva de 10 s para salir del área" |
| 3:30 | Activar el PIR o acercar la mano | "ALARMA: sirena, LED rojo y evento publicado" |
| 4:15 | Pulsar **Silenciar** | "Se calla la sirena pero la alerta queda en SQLite" |
| 4:45 | **Desarmar** y **Abrir cerradura** con PIN | "Comando validado, auditado y confirmado con ACK" |
| 5:15 | Escribir un PIN erróneo | "Rechazado con motivo; a los 3 intentos se bloquea 30 s" |
| 5:45 | `python -m backend.cli historico --horas 6` | "Histórico con timestamp y consultas de agregación" |
| 6:15 | `python -m backend.cli comandos` | "Cada comando con su latencia y estado final" |
| 6:45 | Canal de ThingSpeak | "Los mismos datos en la nube, 8 campos con gráficas" |
| 7:15 | TalkBack con `arm` | "Comando desde la nube hacia el dispositivo" |
| 7:45 | `python -m pytest` | "314 pruebas automatizadas de firmware y backend" |
| 8:30 | Código | "FSM pura, HAL aislado, cliente MQTT propio, tareas asíncronas" |

Consejo: si el WiFi del aula falla, continuar con `--sin-mqtt`; los datos ya
guardados y las pruebas no necesitan red.

---

## 3. Evidencias incluidas en `docs/capturas/`

| Archivo | Qué muestra | Cómo se generó |
|---------|-------------|----------------|
| `01_panel_estado.png` | panel en operación normal | captura real con Chrome headless |
| `02_panel_alarma.png` | panel en ALARMA, con sirena y alertas | captura real tras una intrusión simulada |
| `03_login.png` | pantalla de acceso | captura real |
| `04_cli_historico.png` | histórico por consola | salida real de la CLI renderizada |
| `05_cli_eventos.png` | eventos del sistema | idem |
| `06_cli_estadisticas.png` | agregados y latencias | idem |
| `07_cli_comandos.png` | comandos con su estado | idem |
| `wokwi_01..05_*.png` | circuito, monitor serie y OLED en ARMADO y ALARMA | proyecto real en Wokwi (sección 4) |

Las capturas se regeneran con:

```bat
python scripts\capturar_dashboard.py
python scripts\capturar_wokwi.py --url <enlace del proyecto>
```

---

## 4. Capturas del simulador de Wokwi

Las tomas del circuito, del monitor serie y del OLED se obtuvieron de forma
automatizada desde el proyecto público
<https://wokwi.com/projects/480810097290000385> con
[`scripts/capturar_wokwi.py`](../scripts/capturar_wokwi.py): abre la página en un
navegador headless, pulsa *Play*, acciona el pulsador, provoca la alarma y
captura cada estado mediante el protocolo DevTools.

| Archivo | Qué muestra |
|---------|-------------|
| `wokwi_01_circuito.png` | circuito completo con el nodo en marcha |
| `wokwi_02_serie.png` | monitor serie real: arranque, WiFi y MQTT |
| `wokwi_03_oled_armado.png` | OLED en **ARMADO** con las lecturas |
| `wokwi_04_oled_alarma.png` | OLED en **ALARMA** con la sirena activa |
| `wokwi_05_circuito_alarma.png` | circuito con el LED de alarma encendido |

La pasada de captura confirmó por MQTT real (`centinela/dev01/telemetry`) la
secuencia `ARMING → ARMED → ALARM` con `siren: true` y `alerts: 1`.

### 4.1 Capturas que aún debe tomar el estudiante

| # | Captura | Dónde | Qué debe verse |
|---|---------|-------|----------------|
| 1 | Canal de ThingSpeak | thingspeak.com | los 8 campos con gráficas |
| 2 | TalkBack | thingspeak.com | un comando `arm` en la cola |
| 3 | Repositorio GitHub | github.com | estructura y README renderizado |

> El diagrama `docs/img/circuito.png` sirve de referencia de cableado, pero no
> sustituye a la captura del simulador.

---

## 5. Preguntas frecuentes del jurado

| Pregunta | Respuesta corta |
|----------|-----------------|
| ¿Por qué un backend y no enviar directo a ThingSpeak? | SQLite no cabe en el ESP32; además el backend valida comandos, audita y da histórico local sin depender de la nube. |
| ¿Cómo garantizan la entrega de comandos? | QoS 1 más ACK con identificador; sin ACK en 8 s el comando queda `TIMEOUT`. |
| ¿Qué pasa si se cae el WiFi? | Reintentos con backoff y LWT `offline`; al volver se resuscribe solo. |
| ¿Por qué SSE y no WebSocket? | Un solo sentido, reconexión nativa del navegador y cero dependencias. |
| ¿Es seguro abrir la cerradura por MQTT? | Requiere PIN, solo en DESARMED, se audita y se cierra sola a los 8 s. |
| ¿Cómo probaron el firmware sin hardware? | Dobles de `machine` y un broker MQTT falso sobre TCP: 314 pruebas en CPython. |
| ¿Por qué el nodo no manda la hora? | No tiene RTC ni NTP; el servidor sella cada lectura para que el histórico no se rompa al reiniciar. |
| ¿Cuánto almacena? | Una lectura cada 5 s ≈ 17 000 al día, ~1,5 MB al mes; se purga a los 30 días. |
| ¿Qué pasa con dos dispositivos? | El prefijo incluye `device_id` y el backend escucha `centinela/+/#`. |

---

## 6. Cierre

Entregables mínimos: repositorio en GitHub, ZIP del proyecto Wokwi, paquete
`entregables/Parcial2_IoT_Seguridad.zip`, capturas propias y el canal de
ThingSpeak. La lista oficial está en [`checklist.md`](checklist.md).
