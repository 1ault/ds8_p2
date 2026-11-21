# Entender el proyecto, paso a paso

Guía en lenguaje llano: **qué hace cada pieza, por qué está ahí y por qué la
sirena suena o no suena**. Para la sustentación alcanza con entender las
secciones 1 a 5.

---

## 1. Qué es el sistema en una frase

Un nodo con ESP32 vigila una puerta con sensores; si detecta una intrusión
mientras está **armado**, hace sonar una sirena, enciende LEDs, lo muestra en
un OLED, lo publica por MQTT, lo guarda en SQLite, lo pinta en un panel web y
lo sube a ThingSpeak. Y desde el panel (o la nube) se le pueden mandar órdenes.

---

## 2. Las cuatro capas

```
   ┌──────────────────────────────┐
   │  1. NODO (ESP32, MicroPython)│   sensores + FSM + actuadores
   └──────────────┬───────────────┘
                  │ MQTT (WiFi Wokwi-GUEST)
   ┌──────────────┴───────────────┐
   │  2. BROKER (HiveMQ público)  │   el "cartero": recibe y reparte
   └──────────────┬───────────────┘
                  │ MQTT
   ┌──────────────┴───────────────┐
   │  3. BACKEND (Python + SQLite)│   guarda, valida, panel web (puerto 8000)
   └──────────────┬───────────────┘
                  │ HTTPS
   ┌──────────────┴───────────────┐
   │  4. NUBE (ThingSpeak)        │   gráficas + comandos (TalkBack)
   └──────────────────────────────┘
```

Por qué así: el ESP32 **no** puede guardar meses de datos ni servir una página
web. Entonces el nodo solo mide y reacciona; el backend guarda el histórico y
valida las órdenes.

---

## 3. Recorrido de UN dato (de la temperatura a la gráfica)

1. **`sensors.py`** lee el DHT22 cada 5 s → `{"temp_c": 23.0, "hum_pct": 40.0}`.
2. **`app.py`** arma la telemetría (lecturas + estado + alertas + uptime).
3. **`mqtt_client.py`** la publica en `centinela/dev01/telemetry`.
4. El **broker** la reparte a quien esté suscripto.
5. **`backend/mqtt_bridge.py`** la recibe.
6. **`backend/storage.py`** la guarda en SQLite con fecha y hora del servidor.
7. El **panel web** la empuja al navegador (SSE) y **`cloud.py`** la sube a
   ThingSpeak cada 20 s (8 campos).

Por qué el nodo no manda la fecha: no tiene reloj real. La pone el backend, así
el histórico no se rompe si el ESP32 se reinicia.

---

## 4. Recorrido de UNA orden (del panel al nodo y vuelta)

1. El operador pulsa **Armar** en el panel.
2. `backend/commands.py` publica `{"id": "...", "cmd": "arm"}` en
   `centinela/dev01/cmd`.
3. El nodo lo recibe (`app._al_recibir`), lo mete en el bus interno
   (`bus.py`) y lo procesa (`procesar_comando`).
4. La **FSM** cambia de estado y devuelve **efectos** (`sirena_on`,
   `cerrar_cerradura`, …).
5. `app._aplicar` ejecuta los efectos sobre los actuadores y publica el evento.
6. El nodo responde en `centinela/dev01/ack` (`ok: true/false`).
7. El backend marca el comando como `OK`/`RECHAZADO`/`TIMEOUT` (8 s) y lo
   audita en SQLite.

Es el mismo camino si la orden la escribe el pulsador (origen `boton`) o
ThingSpeak (origen `thingspeak`).

---

## 5. La máquina de estados: quién decide

`fsm.py` es **lógica pura**: no toca GPIO ni red, así se prueba entera.
Devuelve una lista de "efectos" y `app.py` los ejecuta.

| Estado | Qué significa | Sirena | LED |
|--------|---------------|--------|-----|
| `DISARMED` (LISTO) | desactivado, la cerradura abre con PIN | apagada | verde fijo |
| `ARMING` (ARMANDO) | cuenta regresiva de 10 s para salir | apagada | verde parpadea |
| `ARMED` (ARMADO) | vigilando | apagada | verde fijo |
| `ALARM` (ALARMA) | intrusión detectada | **encendida** | rojo parpadea |

Transiciones: `arm` → ARMING; pasan 10 s → ARMED; presencia o temperatura
≥ 45 °C estando armado → ALARM; `disarm` → DISARMED; `mute` silencia sin
desarmar (una alerta nueva la vuelve a encender).

Antirrebote: como mucho **una alerta cada 5 s**, para que un movimiento largo no
infle el contador.

---

## 6. Por qué la sirena suena… o no

Para que suene tienen que pasar **tres cosas, en orden**:

1. **El sistema tiene que estar armado.** Si el OLED dice `LISTO`, el PIR se
   muestra (`Mov SI`) pero **no alerta**: es a propósito, para poder caminar por
   la casa sin que suene.
2. **Tiene que llegar un evento de presencia**: flanco de subida del PIR
   (`Mov no → SI`) o distancia < 80 cm con el HC-SR04.
3. **La FSM pasa a `ALARM`** y emite `sirena_on` → `Buzzer.encender(2400)` →
   PWM de GPIO25 al 50 % → y la tarea de LEDs alterna 2400/2900 Hz cada 300 ms
   (el tono bitonal que se escucha como "wii-u wii-u").

Si el OLED muestra `ALARMA` pero **no se escucha**, el problema ya no es la
lógica: es el audio del simulador (sección 7).

### Probar cada eslabón suelto (REPL de Wokwi: Ctrl-C y pegar)

**a) El buzzer solo** (si suena, el hardware y el PWM están bien):

```python
import machine, time
p = machine.PWM(machine.Pin(25))
p.freq(2400); p.duty_u16(32768)    # 50 % de ciclo: suena
time.sleep(2)
p.duty_u16(0)                      # silencio
```

**b) La FSM sola** (sin sensores ni WiFi):

```python
import fsm
m = fsm.SecurityFSM()
m.handle(0, {"type": "command", "cmd": "arm"})   # -> ARMING
m.tick(11)                                       # -> ARMED
m.handle(11, {"type": "presence", "motivo": "movimiento"})
print(m.estado, m.sonando)                       # ALARM True
```

**c) El PIR solo** (clic en el sensor → Simulate Motion mientras corre):

```python
import machine, time
p = machine.Pin(26, machine.Pin.IN)
for _ in range(40):
    print("PIR", p.value()); time.sleep_ms(250)
```

**d) El pulsador solo**: igual con `machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)`:
en reposo `1`, apretado `0`.

---

### 6.1 El bug que costó días: los modos de pin no son números fijos

`hal.py` usaba `IN = 0` y `OUT = 1`. **En el ESP32 esos números no son los
modos**: `machine.Pin.IN` vale **1** y `machine.Pin.OUT` vale **2**; el **0** es
`GPIO_MODE_DISABLE`. Resultado: el PIR (GPIO26), el eco del HC-SR04 (GPIO18) y
el pulsador (GPIO4) quedaban deshabilitados y **leían siempre 0**.

Síntomas que producía (todos juntos):

- el PIR nunca marcaba `Mov SI` → la alarma no disparaba con movimiento;
- el HC-SR04 nunca veía el eco → el OLED mostraba `Dst --`;
- el pulsador leía 0 desde el arranque → con el código viejo contaba como
  pulsación (el nodo "se armaba solo") y con el nuevo no hacía nada.

La prueba es la comparación directa: en el REPL,
`machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)` leía `1`/`0` al apretar,
mientras la app —con el mismo pin y el mismo cableado— leía `0` siempre.

Arreglo: `hal.entrada()` y `hal.salida()` pasan **`machine.Pin.IN` /
`machine.Pin.OUT`**, que son los valores de cada puerto. Y los dobles de las
pruebas ahora usan los valores del ESP32, para que el error no vuelva
(`tests/test_hal.py`).

LECCIÓN: los valores de esas constantes son *port-specific*; nunca escribirlos
a mano.

## 7. Si el OLED dice ALARMA y no se escucha
Por orden de frecuencia:

1. **Audio del navegador**: Wokwi recién habilita el sonido después de un clic
   en la simulación. Hacé clic en **Play** (o en el diagrama) y volvé a probar.
2. **Pestaña silenciada**: mirá el ícono del altavoz en la pestaña del
   navegador. También el volumen del sistema.
3. **Volumen del buzzer**: en `diagram.json`, `bz1` tiene `"volume": "1"`.
4. **Cableado**: `bz1:2` va a **GPIO25** y `bz1:1` a **GND**.

Si (a) del punto 6 suena y el programa no, entonces la lógica no llegó a
`ALARM`: mirá el OLED y el monitor serie (`estado ... -> ...`).

---

## 8. Los 12 archivos del firmware: qué hace cada uno y por qué está

| Archivo | Qué hace | Por qué existe |
|---------|----------|----------------|
| `main.py` | arranca todo en orden y lanza las tareas | Wokwi ejecuta `main.py` al pulsar Play |
| `config.py` | pines, tiempos, umbrales, tópicos, credenciales | un solo lugar: no hay números mágicos repartidos |
| `hal.py` | envuelve `machine`/`dht`/`network` | así el resto del código se prueba en la PC sin placa |
| `bus.py` | bus de eventos con buzones acotados | desacopla: un consumidor lento no frena al resto |
| `fsm.py` | máquina de estados de seguridad | la decisión de "¿esto es intrusión?" en un solo lugar |
| `sensors.py` | DHT22, PIR, HC-SR04 y LDR con validación y medianas | una lectura mala no debe tumbar el sistema |
| `actuators.py` | LEDs, sirena PWM y servo-cerradura | los efectos de la FSM se vuelven acciones |
| `display.py` | el OLED (estado, lecturas, alertas, sirena) | ver el estado sin mirar la computadora |
| `ssd1306.py` | driver del OLED por I2C | no viene en MicroPython |
| `mqtt_client.py` | cliente MQTT 3.1.1 propio | publica, se suscribe, reconecta y avisa si se cae |
| `net.py` | WiFi con reintentos | si el aula no tiene red, el nodo sigue en local |
| `app.py` | orquestador: sensores → FSM → actuadores → MQTT | pega todas las piezas con tareas asíncronas |

Backend: `main.py` (arranque), `config.py`, `mqtt_bridge.py` (habla con el
broker), `storage.py` (SQLite), `commands.py` (órdenes y ACK), `bus.py`,
`web/app.py` (panel y API), `web/auth.py` (login), `cloud.py` (ThingSpeak),
`cli.py` (consultas por consola).

---

## 9. Los pines (ESP32 DevKit C V4)

| GPIO | Componente |
|------|------------|
| 27 | DHT22 (datos) |
| 26 | PIR (OUT) |
| 5 | HC-SR04 TRIG |
| 18 | HC-SR04 ECHO |
| 34 | LDR (AO, solo entrada) |
| 23 | LED rojo |
| 19 | LED verde |
| 25 | Buzzer (PWM) |
| 13 | Servo de la cerradura |
| 21 / 22 | OLED SDA / SCL |
| 4 | Pulsador (a GND, con pull-up interno) |

---

## 10. Glosario mínimo para la defensa

- **GPIO**: pin del microcontrolador; se configura entrada o salida.
- **PWM**: encendido/apagado muy rápido; la frecuencia define el tono del
  buzzer y el ciclo de trabajo (50 %) el volumen.
- **I2C**: dos cables (SDA/SCL) para el OLED; la dirección es `0x3C`.
- **MQTT**: mensajería por *tópicos* (`centinela/dev01/telemetry`); QoS 1
  confirma la entrega; el *last will* avisa `offline` si el nodo se cae.
- **FSM**: máquina de estados; cada evento produce efectos.
- **SSE**: el servidor empuja eventos al navegador (panel en vivo).
- **ThingSpeak**: canal de 8 campos; **TalkBack** es su cola de comandos.
- **Modo local**: si no hay red, el nodo sigue midiendo, mostrando en el OLED y
  disparando la sirena igual.
