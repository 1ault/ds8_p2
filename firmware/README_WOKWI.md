# Centinela IoT — proyecto para Wokwi

Nodo de seguridad en **ESP32** con **MicroPython**, simulado en
<https://wokwi.com>.

## Cómo importarlo (3 minutos)

1. Entrar a <https://wokwi.com> y crear un proyecto **ESP32 / MicroPython**
   (New Project → ESP32 → MicroPython).
2. En la pestaña de archivos, copiar el contenido de esta carpeta manteniendo
   los nombres:
   - `main.py` (obligatorio: es el archivo que Wokwi ejecuta)
   - `config.py`
   - `hal.py`, `bus.py`, `fsm.py`, `sensors.py`, `actuators.py`,
     `display.py`, `ssd1306.py`, `mqtt_client.py`, `net.py`, `app.py`
3. Abrir la pestaña `diagram.json` y pegar el contenido del archivo
   `diagram.json` de esta carpeta (o importar el proyecto directamente con
   **⋯ → Import / Export**).
4. Pulsar **Play**.

## Qué debe verse

- El OLED muestra `CENTINELA  LISTO` y las lecturas de los cuatro sensores.
- El monitor serie imprime `[centinela] WiFi conectado: 10.13.37.2` y la
  telemetría cada 5 s.
- Al pulsar el botón (o enviar `arm` desde el panel), el LED verde parpadea
  10 s y luego queda fijo: **ARMADO**.
- Al tocar el PIR o acercar la mano al HC-SR04 estando armado, se dispara la
  **ALARMA**: LED rojo intermitente, sirena bitonal y evento en el panel.

## Dos versiones del diagrama

En esta carpeta hay dos archivos de diagrama. **La electricidad es la misma en
los dos**: 13 componentes y 30 conexiones, verificadas con
`python scripts\validar_diagrama.py`.

| Archivo | Cómo se ve | Cuándo usarlo |
|---------|------------|---------------|
| `diagram.json` | componentes sueltos, cables largos hacia el ESP32 | versión de referencia; es la que se capturó para el informe |
| `diagram_placa.json` | los mismos componentes **sobre dos placas de pan** a los lados del ESP32 | cuando se quiere mostrar un montaje físico, tipo prototipo |

Para usar la variante, basta con pegar el contenido de `diagram_placa.json` en
la pestaña `diagram.json` del proyecto. Las placas (`bb1` y `bb2`) van
**detrás** de los módulos, en vertical, y no intervienen en las conexiones: son
la base de montaje, como en un prototipo real donde los módulos se apoyan en la
protoboard y se conectan con cables jumper al ESP32.

### Qué se comprobó de las placas

La geometría se **midió en el simulador**, no se estimó: se abrió el proyecto
público en Chrome headless y se leyeron los rectángulos reales de cada elemento
(`scripts\_medir_placas.py`). Resultados:

| Dato medido | Valor |
|-------------|-------|
| Tamaño de la placa de 830 puntos | **654 × 208 px** (sin girar) |
| Efecto de `rotate: 90` | gira **alrededor de su centro**; la caja queda en `(left + 223, top − 223)` |
| Escala del diagrama | 1 unidad = 1 px |
| Desplazamiento vertical de los componentes en pantalla | +79 px |

Con eso, las coordenadas se calcularon para que cada placa cubra su grupo:

| Placa | `left` | `top` | Caja dibujada | Grupo que cubre | Margen |
|-------|--------|-------|---------------|-----------------|--------|
| `bb1` | −520 | 192 | x[−297..−89] y[−31..623] | sensores x[−290..−96] y[−30..622] | ±7 px |
| `bb2` | 108 | 247 | x[331..539] y[24..678] | actuadores x[340..530] y[20..683] | ±9 px |

Las dos cubren su grupo, están a lados opuestos del ESP32 y no se solapan
(`bb1` termina en −89 y `bb2` empieza en 331). Las 30 conexiones son idénticas
a las del diagrama original.

La placa (654 px) es **9 px más corta** que la columna de actuadores (663 px),
así que ese borde inferior sobresale 5 px por debajo de la placa: se repartió el
margen (4 px arriba, 5 px abajo) porque con una sola placa de 830 puntos no cabe
de otra forma.

El tipo `wokwi-breadboard` **sí existe**: el proyecto del simulador lo carga y
dibuja las dos placas. Si editas el diagrama a mano, recuerda que `left`/`top`
**no** son la esquina visible de la placa cuando está girada: la caja visible
está 223 px a la derecha y 223 px arriba de ese punto.

Para volver a medir después de cualquier cambio:

```bat
python scripts\\_medir_placas.py https://wokwi.com/projects/TU-PROYECTO
python scripts\\validar_diagrama.py
```

```bat
python scripts\generar_diagrama_placa.py
python scripts\validar_diagrama.py
```

## Credenciales de red

`Wokwi-GUEST` (sin contraseña) da salida real a Internet, que es lo que
permite llegar a `broker.hivemq.com`. No hace falta configurar nada.

## Notas de hardware real

- El HC-SR04 y el servo se alimentan a **5 V**; el `ECHO` del HC-SR04 entrega
  5 V y necesita un divisor de tensión antes del GPIO18.
- El DHT22 requiere resistencia de *pull-up* de 10 kΩ en la línea de datos.
