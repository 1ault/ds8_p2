# Instalación y puesta en marcha

Guía para dejar **Centinela IoT** funcionando en local (SQLite + panel) y,
si se quiere, en la nube con ThingSpeak. El SQLite y el broker público **no
necesitan cuenta**; solo Wokwi (simulador) y ThingSpeak (nube) son cuentas.

Ruta del proyecto:

```text
C:\Users\Usuario\code\iot\Parcial2_IoT_Seguridad
```

---

## 0. Resumen: qué necesito según lo que quiera ver

| Quiero ver | Necesito | ¿Cuenta? |
|---|---|---|
| OLED y monitor serie del nodo | Wokwi (web o extensión) | Wokwi, gratis |
| Panel, histórico y gráficas | Backend Python + nodo publicando | Ninguna |
| Datos en la nube | Canal de ThingSpeak + `.env` | ThingSpeak, gratis |
| Entregar el parcial | GitHub + Teams | GitHub, gratis |

---

## 1. Requisitos

| Componente | Versión | Para qué |
|---|---|---|
| Python | 3.10+ (probado con 3.14.7) | backend, SQL y herramientas |
| Navegador | Chrome, Edge o Firefox | panel y Wokwi web |
| Cuenta Wokwi | gratuita | simular el ESP32 |
| Cuenta ThingSpeak | gratuita (opcional) | nube |
| `mpremote` | 1.29 o superior | subir el código a la extensión |

SQLite viene incluido en Python: **no hay que instalar ni configurar nada**.

---

## 2. Backend + SQLite (paso a paso)

```bat
cd C:\Users\Usuario\code\iot\Parcial2_IoT_Seguridad
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m backend.main --seed
```

Abrir <http://127.0.0.1:8000> y entrar con:

```text
usuario: admin
clave:   seguridad2026
```

> En Linux/macOS el único cambio es `source venv/bin/activate`.
> Se usa `venv` (sin punto) para no pisar un `.venv` viejo; cualquiera de los
> dos nombres funciona.

### 2.1 Qué hace `python -m backend.main`

1. Aplica `sql/schema.sql`: crea tablas, vistas e índices si faltan.
2. Registra el dispositivo en `devices`.
3. Conecta a `broker.hivemq.com` y se suscribe a `centinela/+/#`.
4. Arranca las tareas de fondo: mensajes, TalkBack y mantenimiento.
5. Sirve el panel en `127.0.0.1:8000`.

Opciones útiles:

| Opción | Efecto |
|---|---|
| `--seed` | carga datos de demostración |
| `--puerto 8010` | cambia el puerto |
| `--sin-login` | panel abierto (demostración) |
| `--sin-mqtt` | no intenta conectar al broker (modo offline) |

### 2.2 Dónde está el SQL

```text
sql\schema.sql      → tablas, vistas e índices
sql\seed.sql        → datos de demostración
sql\consultas.sql   → 12 consultas de ejemplo
data\centinela.db   → la base real (se crea sola)
```

No hay servidor de base de datos: es un archivo. Para consultarlo:

```bat
python -m backend.cli resumen
python -m backend.cli historico --horas 24 --limite 10
python -m backend.cli eventos --limite 10
python -m backend.cli comandos --limite 10
python -m backend.cli estadisticas
```

Con una interfaz gráfica: **DB Browser for SQLite** (gratis, sin cuenta),
abriendo `data\centinela.db`.

### 2.3 Empezar con la base vacía

```bat
del data\centinela.db*
python -m backend.main
```

Sin `--seed` la base arranca vacía y se llena con lo que publique el nodo.

---

## 3. Nodo en Wokwi web (paso a paso)

1. Entrar a <https://wokwi.com> con la cuenta gratuita.
2. **New Project → ESP32 / MicroPython**.
3. Importar `entregables\Wokwi_Centinela_IoT.zip`.
4. Pulsar **Play**.

El monitor serie debe mostrar:

```text
[centinela] arranque Centinela-Puerta-Principal (dev01) firmware 2.0.0
[centinela] OLED listo en 0x3C
[centinela] WiFi conectado: 10.13.37.2
[centinela] MQTT conectado a broker.hivemq.com:1883
```

> `Wokwi-GUEST` no lleva contraseña y da salida real a Internet: es lo que
> permite llegar al broker público. No hay que configurar nada.

---

## 4. Nodo en VS Code (extensión de Wokwi)

La extensión **no usa el proyecto web**: simula un firmware `.bin` y hay que
subirle los archivos `.py` con `mpremote`.

1. Abrir en VS Code una de estas carpetas:
   - En el repositorio: `firmware/`.
   - En el paquete de entrega: `entregables/Wokwi_Centinela_IoT/`.

   Si usás el repositorio, descargá el firmware
   [`ESP32_GENERIC-20260824-v1.29.0.bin`](https://github.com/wokwi/wokwi-vscode-micropython/raw/main/esp32/ESP32_GENERIC-20260824-v1.29.0.bin)
   dentro de `firmware/` (es el archivo que espera `wokwi.toml`).

2. **F1** → `Wokwi: Request a new License` (una vez, con la cuenta Wokwi).
3. **F1** → `Wokwi: Start Simulator` → elegir `wokwi.toml`.
4. Instalar `mpremote` si falta:

```bat
pip install mpremote
```

5. Con la simulación corriendo y la pestaña visible, ejecutar:

```bat
subir_a_wokwi.bat
```

### 4.1 ¿Para qué sirve `subir_a_wokwi.bat`?

Ese `.bat` **solo se usa con la extensión de VS Code**. Hace esto:

1. Recorre los 12 módulos (`main.py`, `config.py`, `hal.py`, …).
2. Con `mpremote` los copia al sistema de archivos del MicroPython simulado
   por el puerto `rfc2217://localhost:4000`.
3. Reinicia la placa para que arranque `main.py`.

No se usa en Wokwi web: ahí los archivos ya forman parte del proyecto.
No sube `diagram.json`, `wokwi.toml` ni el `.bin`: eso lo maneja la extensión.

**Importante:** el sistema de archivos del simulador **no es persistente**.
Cada vez que cerrás y volvés a abrir la simulación, hay que ejecutar
`subir_a_wokwi.bat` otra vez. La pestaña de Wokwi debe quedar visible o la
simulación se pausa y `mpremote` falla.

Si el puerto 4000 está ocupado, cambiar `rfc2217ServerPort` en `wokwi.toml` y
en el `.bat`.

---

## 5. Demo completa sin Wokwi

```bat
python scripts\demo.py --reset --sembrar --sin-login
```

Levanta el backend con 24 h de histórico y un **nodo emulado que ejecuta el
código real del firmware**. Según el transporte:

| Comando | Transporte | ¿Internet? |
|---|---|---|
| `python scripts\demo.py --reset --sembrar` | HiveMQ real | sí |
| `python scripts\demo.py --reset --sembrar --sin-mqtt` | memoria | no |

Opciones: `--escenario intruso`, `--armar-auto 5`, `--duracion 60`,
`--puerto 8010`, `--salida 4`.

---

## 6. ThingSpeak (nube, opcional)

1. Crear cuenta gratis en <https://thingspeak.com>.
2. **Channels → New Channel** con 8 campos:

| Campo | Nombre | Unidad |
|---|---|---|
| field1 | Temperatura | °C |
| field2 | Humedad | % |
| field3 | Luminosidad | lux |
| field4 | Distancia | cm |
| field5 | Movimiento | 0/1 |
| field6 | Alarma | 0/1 |
| field7 | Estado | 0–3 |
| field8 | Alertas | nº |

3. Copiar **Channel ID** y **Write API Key**.
4. Crear `.env` (copiar `.env.example`) y completar:

```ini
THINGSPEAK_CHANNEL=1234567
THINGSPEAK_WRITE_KEY=XXXXXXXXXXXXXXXX
THINGSPEAK_READ_KEY=...
```

5. Para comandos nube → nodo: **Apps → TalkBack → Add** y agregar:

```ini
THINGSPEAK_TALKBACK_ID=...
THINGSPEAK_TALKBACK_KEY=...
```

6. Reiniciar el backend. El log debe decir `ThingSpeak activo` y el panel
   mostrar **NUBE ON**; el canal recibe un punto cada 20 s.

Comandos de TalkBack: `arm`, `disarm`, `mute`, `unlock:2468`,
`set_config:dist_alarm_cm=120`.

Detalle completo: [`plataforma_nube.md`](plataforma_nube.md).

---

## 7. Verificación de punta a punta

1. Backend corriendo (`python -m backend.main --seed`).
2. Nodo en Wokwi con **Play**.
3. En el panel:
   - **MQTT OK** y nodo `online`.
   - Lecturas de temperatura, humedad, luz y distancia.
   - Histórico, eventos y comandos.
4. En SQL:

```bat
python -m backend.cli resumen
python -m backend.cli historico --horas 24
```

5. En ThingSpeak: el canal recibe datos.
6. Probar un comando: **Armar** desde el panel → el nodo pasa a `ARMING` y
   luego `ARMED`, con ACK.
7. Provocar el PIR o acercar la mano → **ALARMA**, sirena y evento crítico.

---

## 8. Cuentas

| Recurso | ¿Cuenta? | Para qué |
|---|---|---|
| SQLite | **No** | Archivo local; Python ya lo trae |
| Backend / panel | **No** | Corre en la PC |
| HiveMQ público | **No** | Broker abierto |
| Wokwi | Sí, gratis | Simulador y licencia de la extensión |
| ThingSpeak | Sí, gratis | Solo para la nube |
| GitHub | Sí, gratis | Solo para entregar |

---

## 9. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `ModuleNotFoundError: aiohttp` | no se activó el entorno | `venv\Scripts\activate` y reinstalar |
| El panel dice `MQTT OFF` | broker inalcanzable o firewall | revisar Internet; para demo usar `--sin-mqtt` |
| `database is locked` | dos backends sobre la misma base | cerrar el otro proceso |
| No aparecen lecturas | el nodo no publica | revisar monitor serie y prefijo `centinela` |
| Wokwi no conecta | falta `diagram.json` | importar el ZIP completo |
| `mpremote` da `TransportError` | pestaña de Wokwi oculta o placa arrancando | dejar la pestaña visible y esperar |
| OLED negro | SDA/SCL mal o dirección distinta | SDA 21, SCL 22, dirección `0x3C` |
| `pip` falla al crear el venv | permisos del temporal | crear el venv en una ruta local, sin OneDrive |

### Notas de hardware real

- El HC-SR04 y el servo se alimentan a **5 V**; el `ECHO` entrega 5 V y necesita
  un divisor de tensión antes del GPIO18.
- El DHT22 requiere resistencia *pull-up* de 10 kΩ en la línea de datos.
- El GPIO34 es solo entrada: correcto para el LDR, inservible para actuadores.
- El OLED conviene alimentarlo a **3.3 V** en una placa real.

---

## 10. GitHub y Teams

Repositorio: <https://github.com/1ault/ds8_p2>

```bat
git clone https://github.com/1ault/ds8_p2.git
cd ds8_p2
```

Para publicar cambios:

```bat
git add .
git commit -m "descripcion del cambio"
git push origin main
```

Los ZIP y PDF no se versionan: se descargan del
[Release](https://github.com/1ault/ds8_p2/releases/latest) y se adjuntan en
Teams. Antes de subir, comprobar que **no** se publican `.env`, `data/*.db` ni
`*.bin` (ya están en `.gitignore`).
