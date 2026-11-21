# Wokwi en VS Code (extensión) — puesta en marcha

Esta carpeta (`firmware/`) **ya está preparada** para la extensión *Wokwi
Simulator* de VS Code:

| Archivo | Para qué |
|---------|----------|
| `wokwi.toml` | le dice a la extensión qué firmware cargar (`ESP32_GENERIC-20260824-v1.29.0.bin`) y el puerto serie 4000 |
| `diagram.json` | el circuito (13 componentes, 30 conexiones) |
| `ESP32_GENERIC-20260824-v1.29.0.bin` | MicroPython ya compilado (1,7 MB) |
| los 12 `.py` | el programa del nodo, los mismos que edita el repositorio |

> **No crees otra carpeta.** Una copia aparte se desincroniza del repositorio
> (eso fue justo lo que pasó cuando el `app.py` de Wokwi quedó viejo).

## 1. Una sola vez

1. Instalar la extensión **Wokwi Simulator** en VS Code.
2. `F1` → **Wokwi: Request a License** → licencia gratuita para uso personal.
3. Instalar `mpremote` (es el que copia los `.py` al MicroPython simulado):

```bat
C:\Users\Usuario\code\iot_p2\.venv\Scripts\python.exe -m pip install mpremote
```

Si querés la versión que coincide con el firmware: `pip install mpremote==1.29.0`.

## 2. Cada vez que quieras simular

1. VS Code → **File → Open Folder** → `C:\Users\Usuario\code\iot_p2\firmware`.
2. `F1` → **Wokwi: Start Simulator** (o abrir `diagram.json` y pulsar Play).
3. **Dejar la pestaña de Wokwi visible**: si se oculta, la simulación se pausa
   y el puerto serie deja de responder.
4. Doble clic en **`subir_a_wokwi.bat`** (o `Terminal → Run Task`). Sube los 12
   módulos y reinicia el nodo.

El filesystem del simulador **no es persistente**: cada vez que arrancás la
simulación hay que volver a ejecutar el `.bat`. Por eso el script existe.

## 3. Qué debe verse en el monitor serie

```
[centinela] arranque Centinela-Puerta-Principal (dev01) firmware 2.0.2
[centinela] OLED listo en 0x3C
[centinela] WiFi conectado: 10.13.2.2
[centinela] controlador iniciado: Centinela-Puerta-Principal
[centinela] boton nivel 1
[centinela] latido estado=DISARMED boton=1 mqtt=... alertas=0
```

Al apretar el pulsador:

```
[centinela] boton nivel 0
[centinela] boton: pulsacion
[centinela] estado DISARMED -> ARMING (arm desde boton)
```

Si `MQTT` no conecta, el nodo **sigue funcionando**: la sirena, el OLED, el PIR
y el pulsador son locales. El broker público se cae seguido.

## 4. Probar piezas sueltas en el REPL

En la terminal del simulador, **Ctrl+C** corta `main.py` y deja el REPL:

```python
# el buzzer solo
import machine, time
p = machine.PWM(machine.Pin(25))
p.freq(2400); p.duty_u16(32768)
time.sleep(2)
p.duty_u16(0)

# la FSM sola
import fsm
m = fsm.SecurityFSM()
m.handle(0, {"type": "command", "cmd": "arm"})
m.tick(11)
m.handle(11, {"type": "presence"})
print(m.estado, m.sonando)      # ALARM True

# el pulsador solo (apretar mientras corre)
import machine, time
b = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)
for _ in range(40):
    print("BTN", b.value()); time.sleep_ms(250)
```

Para volver al programa: **Ctrl+D** (o `import machine; machine.reset()`), y si
hace falta volvé a correr el `.bat`.

## 5. Diferencias con Wokwi web

| | Wokwi web | Wokwi en VS Code |
|---|---|---|
| Archivos | se pegan en el editor del navegador | se suben desde esta carpeta |
| Al cambiar un `.py` | hay que pegarlo de nuevo a mano | se vuelve a correr el `.bat` |
| Serie/REPL | pestaña del navegador | terminal de VS Code |
| Botón / PIR | clic en el dibujo | clic en el dibujo (misma simulación) |

El motor de simulación es el mismo; la ventaja de VS Code es que el código
fuente es el del repositorio, sin copias.
