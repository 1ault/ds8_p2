# Fase 0 — Inventario de la maqueta física

Documento previo a escribir código. Responde: **qué hay**, **qué falta** y
**qué cambia** respecto al diagrama de Wokwi.

- Repo base: `iot_p2` (firmware 2.0.5, 337 pruebas en verde)
- Escenario: Sistema de Seguridad — Detección y alertas

---

## 1. Placas disponibles

| Placa | Chip | Notas | Papel propuesto |
|---|---|---|---|
| **Elegoo ESP32 DevKit** | ESP32-D0WD-V3, 4 MB | GPIO idénticos al diagrama de Wokwi | **Nodo de la maqueta (`dev02`)** |
| Keyestudio **KS5016** | ESP32-WROOM-32E, 4 MB | tiene relé a bordo, conectores G/V/S | nodo alternativo o actuador de relé |
| 3× GOOUUU **ESP32-S3-CAM** | ESP32-S3, 8 MB PSRAM | cámara OV3660, ya funcionando | **proyecto aparte** (vigilancia) |

**Decisión propuesta:** el nodo de la maqueta va en la **Elegoo**, porque
sus pines coinciden con el diagrama de Wokwi. Así el mapa de pines no cambia
y el perfil `fisico` solo toca WiFi, broker y calibración.

---

## 2. Tabla de mapeo (simulación → física)

| Componente | GPIO Wokwi | GPIO física (Elegoo) | Diferencia |
|---|---|---|---|
| DHT22 (temp/humedad) | 27 | 27 | ⚠️ **no hay DHT22** (ver §4) |
| PIR HC-SR501 | 26 | 26 | 30–60 s de calentamiento |
| HC-SR04 TRIG | 5 | 5 | igual |
| HC-SR04 ECHO | 18 | 18 | ⚠️ **divisor de tensión** (sale a 5 V) |
| LDR | 34 | 34 | ADC1, solo entrada; recalibrar con luz real |
| LED rojo | 23 | 23 | igual |
| LED verde | 19 | 19 | igual |
| Buzzer | 25 | 25 | módulo con transistor (5 V) |
| Servo SG90 | 13 | 13 | fuente de 5 V aparte |
| OLED SDA | 21 | 21 | ⚠️ **no hay SSD1306** (ver §4) |
| OLED SCL | 22 | 22 | idem |
| Pulsador | 4 | 4 | igual |

---

## 3. Lo que sí hay (confirmado en el inventario físico)

| Componente | Cant. | Estado | Notas |
|---|---|---|---|
| PIR HC-SR501 | 2 | ✅ | probado, entrega 3.3 V |
| HC-SR04 | 2 | ✅ | a 3.3 V da lecturas erráticas; a 5 V hay que dividir ECHO |
| LDR (fotocélula) | 1 | ✅ | conector G/V/A |
| Pulsadores | varios | ✅ | conectores G/V/4 y G/V/8 |
| Servos SG90 | ~6 | ✅ | 5 V, pico 700 mA |
| Buzzer | 1 | ✅ | módulo de 3 pines, suena a 5 V |
| LEDs rojo/verde | varios | ✅ | con resistencia en el kit |
| LCD1602 I2C | 1 | ✅ | alternativa al OLED |
| Display 7 segmentos | 1 | ✅ | no aplica |
| Relé HW-307 (10 A) | 1 | ✅ | para conmutar carga externa |
| Fuente 5 V 1 A | 1 | ✅ | para servo y HC-SR04 |

---

## 4. Los dos huecos que hay que decidir

### 4.1 Sensor de temperatura y humedad

```
Wokwi:   DHT22  (1-wire, GPIO27)
Física:  HAY DHT22  ✅  (confirmado por el usuario)
```

Sin cambios en el código.

### 4.2 Pantalla

```
Wokwi:   SSD1306 OLED 128×64 (I2C 0x3C)
Física:  NO HAY SSD1306  →  se ignora
```

`display.py` ya contempla la ausencia de pantalla: `Pantalla.__init__` atrapa la
excepción, deja `disponible = False` y cada refresco devuelve `False`. El nodo
arranca y opera sin OLED sin tocar una línea.

Falta confirmar con una prueba explícita que `app.py` sigue vivo sin pantalla.

### 4.3 Decisión tomada

```
DHT22 sí · SSD1306 no (ignorado) · nodo en la Elegoo ESP32 DevKit
```

---

## 5. Diferencias eléctricas a resolver (Fase 2)

| Tema | Acción |
|---|---|
| HC-SR04 a 5 V | divisor 1 kΩ + 2 kΩ en ECHO, o alimentarlo a 3.3 V y filtrar |
| DHT22 | pull-up de 10 kΩ en el pin de datos |
| Servo SG90 | fuente de 5 V aparte, GND común con el ESP32 |
| PIR | 30–60 s de calentamiento; jumper de retrigger |
| LDR | recalibrar `LDR_RL10_KOHM` con luz real |
| Pines a evitar | 6–11 (flash), 0/2/12/15 (strapping), 1/3 (UART) |

Ninguno de los pines del mapa cae en zona prohibida.

---

## 6. Decisiones cerradas

| Tema | Decisión |
|---|---|
| Placa del nodo | **Elegoo ESP32 DevKit** (pines idénticos a Wokwi) |
| DHT22 | **sí hay** |
| SSD1306 | **no hay** → el nodo arranca sin pantalla |
| Código | se **reutiliza** todo `iot_p2`; la maqueta no crea copia |

## 7. Orden de trabajo

1. **Hito 1**: el firmware actual corre en la Elegoo con el BOM de Wokwi
   (DHT22, PIR, HC-SR04, LDR, LEDs, buzzer, servo, pulsador). Sin pantalla.
2. **Hito 2**: piezas extra de la maqueta (a definir).

Los extras entran **después** del hito 1: primero tiene que funcionar lo mismo
que en la simulación, con las 337 pruebas en verde.

## 8. Preguntas abiertas

1. ¿Tienes **resistencias de 1 kΩ y 2 kΩ** para el divisor del ECHO del HC-SR04?
2. ¿Tienes **pull-up de 10 kΩ** para el DHT22?
3. ¿Qué **piezas extra** quieres agregar en el hito 2?

