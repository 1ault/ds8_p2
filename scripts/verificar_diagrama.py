"""Valida que el diagram.json de Wokwi conecte cada pata con el GPIO correcto."""

import json
import re
import sys
from pathlib import Path

ruta = Path(sys.argv[1])
datos = json.loads(ruta.read_text(encoding="utf-8"))

padre = {}


def find(x):
    padre.setdefault(x, x)
    while padre[x] != x:
        padre[x] = padre[padre[x]]
        x = padre[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        padre[ra] = rb


def conectado(a, b):
    return find(a) == find(b)


for conexion in datos["connections"]:
    a, b = conexion[0], conexion[1]
    if a.startswith("$") or b.startswith("$"):
        continue
    union(a, b)

# Interior de las placas de pan: cada columna une sus 5 huecos por mitad.
placas = {p["id"] for p in datos["parts"] if p["type"].startswith("wokwi-breadboard")}
for placa in placas:
    for columna in range(1, 31):
        for mitad, filas in (("t", "abcde"), ("b", "fghij")):
            primera = "%s:%d%s.%s" % (placa, columna, mitad, filas[0])
            for fila in filas[1:]:
                union(primera, "%s:%d%s.%s" % (placa, columna, mitad, fila))
    for riel in ("tp", "tn", "bp", "bn"):
        primera = "%s:%s.1" % (placa, riel)
        for hueco in range(2, 31):
            union(primera, "%s:%s.%d" % (placa, riel, hueco))

fallos = []


def revisar(etiqueta, pata, esperado):
    ok = conectado(pata, esperado)
    print(("  OK   " if ok else "  FALLA") + "  %-22s %s -> %s" % (etiqueta, pata, esperado))
    if not ok:
        fallos.append(etiqueta)


print("== alimentacion ==")
for etiqueta, pata, esperado in (
    ("DHT22 VCC", "dht1:VCC", "esp:3V3"),
    ("DHT22 GND", "dht1:GND", "esp:GND.2"),
    ("PIR VCC", "pir1:VCC", "esp:3V3"),
    ("PIR GND", "pir1:GND", "esp:GND.2"),
    ("LDR VCC", "ldr1:VCC", "esp:3V3"),
    ("LDR GND", "ldr1:GND", "esp:GND.2"),
    ("HC-SR04 VCC", "ultrasonic1:VCC", "esp:5V"),
    ("HC-SR04 GND", "ultrasonic1:GND", "esp:GND.2"),
    ("OLED VCC", "oled1:VCC", "esp:5V"),
    ("OLED GND", "oled1:GND", "esp:GND.2"),
    ("Servo V+", "servo1:V+", "esp:5V"),
    ("Servo GND", "servo1:GND", "esp:GND.2"),
    ("Buzzer GND", "bz1:1", "esp:GND.2"),
):
    revisar(etiqueta, pata, esperado)

print("== senales ==")
for etiqueta, pata, esperado in (
    ("DHT22 DATA", "dht1:SDA", "esp:27"),
    ("PIR OUT", "pir1:OUT", "esp:26"),
    ("HC-SR04 TRIG", "ultrasonic1:TRIG", "esp:5"),
    ("HC-SR04 ECHO", "ultrasonic1:ECHO", "esp:18"),
    ("LDR AO", "ldr1:AO", "esp:34"),
    ("LED rojo", "led1:A", "esp:23"),
    ("LED verde", "led2:A", "esp:19"),
    ("Buzzer", "bz1:2", "esp:25"),
    ("Servo PWM", "servo1:PWM", "esp:13"),
    ("OLED SDA", "oled1:SDA", "esp:21"),
    ("OLED SCL", "oled1:SCL", "esp:22"),
    ("Boton", "btn1:2.r", "esp:4"),
):
    revisar(etiqueta, pata, esperado)

print("== retorno a GND ==")
for etiqueta, pata, esperado in (
    ("LED rojo R", "r1:2", "esp:GND.2"),
    ("LED verde R", "r2:2", "esp:GND.2"),
    ("Boton GND", "btn1:1.r", "esp:GND.2"),
):
    revisar(etiqueta, pata, esperado)

print("== resistencias de LED ==")
for etiqueta, pata, esperado in (
    ("LED rojo catodo", "led1:C", "r1:1"),
    ("LED verde catodo", "led2:C", "r2:1"),
):
    revisar(etiqueta, pata, esperado)

print()
if fallos:
    print("FALLOS: %d -> %s" % (len(fallos), ", ".join(fallos)))
    sys.exit(1)
print("DIAGRAMA OK: todas las patas llegan al pin esperado")
