# Plataforma en la nube: ThingSpeak

ThingSpeak cumple dos funciones en el sistema:

1. **Visualización en la nube**: un canal de 8 campos con gráficas históricas.
2. **Recepción de comandos desde la nube**: la aplicación *TalkBack* permite
   encolar órdenes que el backend recoge y envía al nodo.

Sin claves configuradas el sistema funciona igual en local; la nube es un extra
que se activa con cuatro variables de entorno.

---

## 1. Crear el canal

1. Entrar a <https://thingspeak.com> y crear una cuenta gratuita.
2. **Channels → New Channel** con estos 8 campos:

| Campo | Nombre | Unidad | Qué guarda |
|-------|--------|--------|------------|
| field1 | Temperatura | °C | `temp_c` |
| field2 | Humedad | % | `hum_pct` |
| field3 | Luminosidad | lux | `lux` |
| field4 | Distancia | cm | `dist_cm` |
| field5 | Movimiento | 0/1 | `motion` |
| field6 | Alarma | 0/1 | `alarm` |
| field7 | Estado | 0–3 | `DISARMED`=0, `ARMING`=1, `ARMED`=2, `ALARM`=3 |
| field8 | Alertas | nº | `alerts` |

3. Guardar y copiar el **Channel ID** y la **Write API Key**.
4. Ponerlos en `.env`:

```ini
THINGSPEAK_CHANNEL=1234567
THINGSPEAK_WRITE_KEY=XXXXXXXXXXXXXXXX
```

Al arrancar, el backend registra en el log `ThingSpeak activo (canal ...)` y
empieza a subir una lectura cada 20 s.

> El plan gratuito admite **1 actualización cada 15 s**. El backend usa 20 s y
> además descarta envíos dentro del intervalo (`omitidos`), de modo que nunca
> se pierde la cuota por ráfagas.

---

## 2. Activar TalkBack (comandos nube → dispositivo)

1. En el canal: **Apps → TalkBack → Add a TalkBack app**.
2. Copiar el **TalkBack ID** y la **API Key**.
3. Configurar:

```ini
THINGSPEAK_TALKBACK_ID=9876
THINGSPEAK_TALKBACK_KEY=YYYYYYYYYYYY
TALKBACK_INTERVAL_S=15
```

4. Escribir comandos en la cola de TalkBack con este formato:

| Texto en TalkBack | Comando resultante |
|-------------------|--------------------|
| `arm` | armar el sistema |
| `disarm` | desarmar |
| `mute` | silenciar la sirena |
| `unlock:2468` | abrir la cerradura con PIN |
| `set_config:dist_alarm_cm=120` | cambiar el umbral de distancia |

El backend consulta la cola cada 15 s y ejecuta el comando por el mismo camino
auditado que usa el panel, con lo que también obtiene ACK y latencia.

---

## 3. Cómo se comporta ante fallos

| Situación | Comportamiento |
|-----------|----------------|
| Sin claves | `activa = False`; todo funciona en local |
| ThingSpeak responde `0` | se cuenta como error y se registra el motivo |
| Timeout de red | error controlado; no bloquea el bucle de mensajes |
| Cuota agotada | los envíos se omiten hasta el siguiente intervalo |
| TalkBack sin comandos | la consulta devuelve `None` y no pasa nada |

Ninguna llamada a la nube puede tumbar el backend: todas están envueltas en
`try/except` y devuelven `False`, y el estado se puede consultar en
`/api/estado` (bloque `nube`).

---

## 4. Verificación rápida

```bat
:: 1. arrancar
python -m backend.main

:: 2. ver el estado de la nube en el panel
::    (píldora "Nube" y tarjeta "Estado del sistema")

:: 3. forzar un envío desde la consola de Python
python -c "import asyncio; from backend import config, cloud; cfg=config.cargar(); n=cloud.NubeThingSpeak(cfg); print(asyncio.run(n.subir({'temp_c':24,'hum_pct':55,'lux':100,'dist_cm':150,'motion':False,'alarm':False,'state':'ARMED','alerts':0})))"
```

Si el canal está bien configurado, el comando anterior imprime `True` y aparece
una entrada nueva en ThingSpeak.

---

## 5. Alternativas equivalentes

El backend aísla la nube en `backend/cloud.py` con dos operaciones
(`subir` y `siguiente_comando`). Cambiar a **Adafruit IO**, **AWS IoT** o
**Azure IoT Hub** implica escribir una clase con esa misma interfaz y
seleccionarla en `backend/main.py`; ni el firmware ni el panel cambian.
