# Estado actual — Centinela IoT (Parcial #2, escenario 4)

Última actualización: 2026-11-19
Carpeta: `C:\Users\Usuario\code\iot_p2`

## Publicado

- Repositorio: <https://github.com/1ault/ds8_p2>
- Release: <https://github.com/1ault/ds8_p2/releases/tag/v2.0.0>
- Último commit: `b2c23e8` — `fix(fsm): una alerta nueva reactiva la sirena tras mute`
- Wokwi: <https://wokwi.com/projects/480810097290000385>
- Pruebas locales: **337 passed**
- Firmware: **2.0.5** (el número aparece en la primera línea del monitor serie)
- Cumplimiento de los requisitos del PDF: `docs/cumplimiento_requisitos.md`
- Publicado: `163a7a1` (documentación + fix de memoria del WiFi)

## Problema que se resolvió: el PIR no disparaba la alarma

Síntoma: al simular movimiento en el PIR, el OLED seguía en `ARMADO` con
`Mov SI`, `Alerta 0` y `Sir. silencio`, y el buzzer no sonaba. El PWM directo
en GPIO25 sí sonaba: el hardware estaba bien.

### Causa raíz

El PIR de Wokwi deja `OUT` en ALTO **5 s** (atributo `delayTime`), y el
firmware le agrega 1,5 s de mantenimiento. El controlador detectaba el
**flanco de subida** y llamaba a la FSM, pero `fsm._presencia` solo atiende en
`ARMADO`/`ALARMA`. Si el pulso empezaba durante la **cuenta regresiva de
salida** (`ARMING`), la FSM lo ignoraba —correcto— y el controlador ya había
marcado el flanco como consumido (`_movimiento_prev = True`). Al quedar
`ARMADO` no volvía a haber flanco: la misma presencia quedaba invisible **para
siempre** y la sirena nunca arrancaba. Ese es exactamente el estado
`ARMADO + Mov SI + Alerta 0 + Sir. silencio`.

Se reprodujo sin Wokwi con `scripts/diagnostico_pir.py` (casos 3 y 4 fallaban)
y se verificó la corrección con los 6 casos.

### Otros dos defectos encontrados

1. **Reloj de 1 segundo.** En el ESP32 `time.time()` devuelve segundos
   enteros. Los períodos de muestreo de `config.py` (PIR 0,15 s, HC-SR04
   0,5 s) se redondeaban a 1 s: el PIR se leía **1 vez por segundo** y el
   contador `Salida Ns` saltaba de segundo en segundo.
2. **Auto-armado.** `_al_recibir` aceptaba comandos **retenidos** del broker:
   un `arm` publicado con *retain* en `centinela/dev01/cmd` rearmaba el nodo
   en cada arranque. Además, el botón asumía "suelto" en la primera lectura:
   si GPIO4 ya estaba en 0 al arrancar, el nodo se armaba solo.

## El bug que impedía arrancar en Wokwi (y cómo se resolvió)

El nodo arrancaba y moría en el WiFi:

    E wifi: Expected to init 10 rx buffer, actual is 1
    OSError: WiFi Out of Memory

Causa: en MicroPython **los docstrings se cargan en RAM** (los comentarios `#`
no). La documentación había agregado 42,5 KB de docstrings y el driver WiFi no
conseguía sus 10 buffers contiguos.

Arreglo: los **168** docstrings pasaron a comentarios (`#`) en los 12 módulos,
con el mismo contenido y **0 B** de RAM. Además `main.py` hace `gc.collect()`
antes de crear el WiFi y `net.py` recolecta y reintenta si la WLAN falla por
memoria. Versión **2.0.5**.

## El bug de fondo (encontrado al final): los modos de pin

`hal.py` usaba `IN = 0` y `OUT = 1`, pero **en el ESP32 esos números no son los
modos**: `machine.Pin.IN` = 1 y `machine.Pin.OUT` = 2; el **0** es
`GPIO_MODE_DISABLE`. Con eso, las tres entradas digitales quedaban
deshabilitadas y **leían siempre 0**:

- PIR (GPIO26) → nunca `Mov SI` → la alarma no disparaba con movimiento;
- eco del HC-SR04 (GPIO18) → `Dst --` desde el arranque;
- pulsador (GPIO4) → 0 fijo: con el código viejo contaba como pulsación (el
  nodo "se armaba solo") y con el nuevo no hacía nada.

Prueba directa: en el REPL `machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)`
leía 1/0 al apretar; la app, con el mismo pin y cableado, leía 0 siempre.

Arreglo: `hal.entrada()`/`hal.salida()` pasan `machine.Pin.IN`/`machine.Pin.OUT`
(valores propios de cada puerto), los dobles de prueba usan los valores del
ESP32 y `tests/test_hal.py` lo fija. Los LEDs también quedan bien: antes se
creaban en modo 1 (que en el ESP32 es *entrada*).

## Cambios de esta sesión

| Archivo | Cambio |
|---------|--------|
| `firmware/app.py` | Presencia **pendiente**: si el flanco llega en `ARMING`, se resuelve al quedar `ARMADO` (métodos `_marcar_presencia` y `_resolver_presencia`). Reloj `reloj_monotonico()` con `ticks_ms()` (resolución de ms). Comandos retenidos ignorados. Pulsador: sondeo cada **20 ms**, traza `boton nivel 0/1` y latido `latido estado=... boton=... mqtt=...` cada 10 s + confirmación de 2 muestras (un clic corto ya no se pierde) y el estado inicial se adopta sin contarlo como pulsación. **Traza del origen**: `estado X -> Y (arm desde boton|mqtt|thingspeak)` y `comando MQTT recibido: ...`. |
| `firmware/config.py` | `DIST_MAX_CM` 350 → **410 cm** (el HC-SR04 mide hasta 400 y Wokwi arranca en 400: descartaba la lectura y el OLED mostraba `Dst --`). `BUTTON_POLL_S = 0.02`. `FIRMWARE_VERSION` → **2.0.2** (marca visible en el monitor serie). `MQTT_CLIENT_ID` → `centinela-ault-dev01` (id unico: con el publico broker.hivemq.com, dos nodos con el mismo id se expulsan y el serie repite `fallo de conexion MQTT`). `LATIDO_S = 10`. |
| `firmware/hal.py` | **Arreglo del bug de fondo**: `entrada()`/`salida()` usan `machine.Pin.IN`/`machine.Pin.OUT` en vez de 0/1. Se agregó `pull_down()` y se documentó por qué nunca hay que escribir esos números a mano. |
| `tests/test_hal.py` | **Nuevo (7 pruebas)**: los modos de entrada/salida son los del puerto, el pulsador lleva pull-up, el PIR y el eco quedan como entrada. Los dobles ahora usan los valores del ESP32 (IN=1, OUT=2). |
| `docs/entender_el_proyecto.md` | **Nuevo.** Explicación paso a paso del sistema, la sirena y este bug (§6.1). |
| `firmware/README_VSCODE.md` | **Nuevo.** Puesta en marcha con la extensión de Wokwi en VS Code. |
| `firmware/subir_a_wokwi.bat` | Reescrito: detecta el Python del venv, verifica los archivos y sube los 12 módulos + reset. |
| `firmware/sensors.py` | La suite no se congela si el reloj monotónico da la vuelta (~12 días). |
| `tests/test_app.py` | +10 pruebas: presencia en la cuenta regresiva, presencia estando `DESARMADO`, comando retenido, botón bajo al arrancar, clic corto, traza del origen, reloj por defecto, presencia cercana diferida. |
| `tests/test_sensors.py` | +1 prueba: vuelta del reloj monotónico; +1 prueba: fondo de escala de 400 cm del HC-SR04. |
| `scripts/diagnostico_pir.py` | **Nuevo.** Reproduce PIR → FSM → OLED/buzzer con los módulos reales (6 escenarios, código 1 si alguno falla). |
| `docs/cumplimiento_requisitos.md` | **Nuevo.** Matriz requisito del PDF → evidencia → estado, más los pasos que faltan. |
| `docs/guia_demo.md` | Guion actualizado y los dos clics de Wokwi (PIR y deslizador del HC-SR04). |

No se tocó `fsm.py`: el diseño "durante la cuenta regresiva no se alerta"
está documentado y probado (`test_presencia_durante_armado_no_dispara`). Lo
que se arregló es que la presencia **no se pierda**, no que la FSM cambie.

## Cómo probarlo en Wokwi (el paso que falta)

1. Copiar al proyecto de Wokwi **dos** archivos: `firmware/app.py` y
   `firmware/config.py` (no cambió ninguna firma).
2. **Play** y mirar la **primera línea** del monitor serie:
   `[centinela] arranque ... firmware 2.0.2`. Si dice `2.0.0`, los archivos no
   se reemplazaron.
3. Pulsar `btn1` (clic corto alcanza) y **esperar a que el OLED diga
   `ARMADO`** (10 s de cuenta regresiva). La serie muestra el origen:
   `estado DISARMED -> ARMING (arm desde boton)`.
4. Clic en el PIR → **Simulate Motion**. En menos de un segundo:
   - OLED: `ALARMA` / `Mov SI` / `Alerta 1` / `Sir. SIRENA`.
   - Sirena bitonal (2,4 / 2,9 kHz) y LED rojo intermitente.
   - Serie: `[centinela] Sirena activada`.

### Si el nodo se arma solo, la serie dice quién fue

| Línea en la serie | Qué significa | Qué hacer |
|-------------------|---------------|-----------|
| `estado DISARMED -> ARMING (arm desde boton)` | el pulsador vio un 0 (clic real o ruido) | revisar el cableado de GPIO4 |
| `estado DISARMED -> ARMING (arm desde mqtt)` | alguien publicó `arm` en `centinela/dev01/cmd` | **el tópico es público**: todos los del curso usan `centinela/dev01/cmd`, así que otro cliente puede armar/desarmar este nodo. Solución: `DEVICE_ID` único (`.env` y `config.py`) o HiveMQ Cloud con credenciales |
| `comando retenido ignorado: ...` | quedó un `arm` con *retain* en el broker | publicar un mensaje vacío con retain en `centinela/dev01/cmd` para limpiarlo |
| `boton: pulsacion` | el pulsador sí está funcionando | — |
5. Si se simula movimiento **durante** la cuenta regresiva, la alarma suena
   al terminar la cuenta (la presencia queda pendiente, ya no se pierde).

Comprobación de cableado en el REPL (Ctrl-C y pegar):

```python
import machine, time
p = machine.Pin(26, machine.Pin.IN)
for _ in range(20):
    print("PIR", p.value()); time.sleep_ms(500)
```

Con "Simulate Motion" la línea debe pasar a `PIR 1`.

## Pendientes

- **ThingSpeak**: `.env` sin claves; panel en `NUBE OFF`; TalkBack sin configurar.
  Es el único requisito del PDF que falta; pasos en `docs/cumplimiento_requisitos.md` §4.1.
- **Teams**: no se subió.
- **Sustentación oral**: pendiente (50 % de la nota); guion en `docs/guia_demo.md`.
- **`scripts/validar_diagrama.py`**: falla por las conexiones al pseudo-parte
  `$serialMonitor` de Wokwi y por comparar la variante `diagram_placa.json`.
  Es anterior a esta sesión y no afecta al circuito.
- Los **generadores** de la documentación (`scripts/build_*.py`) ya dicen
  "2–400 cm" y "324 pruebas", pero los `.docx`/`.pdf` que están en
  `docs/manuales/` se construyeron antes: hay que volver a ejecutar los
  `build_*` (y exportar a PDF) si se entregan otra vez.
- Commit y push de esta sesión: pendientes de autorización.

## Reglas

- **No hacer commit ni push sin autorización explícita.**
- `AGENTS.md` **no** va al repositorio.
- Argumentos con nombre obligatorios en las llamadas.
- No subir `.env`, `data/*.db`, `*.bin`, ZIPs ni credenciales.
- Responder en español, paso a paso, pocas palabras.

## Entorno

```bat
cd C:\Users\Usuario\code\iot_p2
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe -m pytest -q
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe scripts\diagnostico_pir.py
```

Backend:

```bat
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe -m backend.main --seed
```

Panel: <http://127.0.0.1:8000> — `admin` / `seguridad2026`.

## Archivos importantes

- `firmware/` — 12 módulos + `diagram.json` (y la variante `diagram_placa.json`).
- `backend/`, `sql/`, `tests/`, `scripts/`, `docs/`.
- `entregables/` — ZIP del proyecto, ZIP de Wokwi, manuales, manifiesto.
- `Wokwi_Centinela_IoT_480810097290000385.zip` — ZIP para importar en Wokwi.
- `asignacion/Parcial_2.pdf` / `.txt` — enunciado.
- `asignacion/wokwi_diagram.json` — diagrama real del proyecto Wokwi.
