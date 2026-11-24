# Controlador del nodo: une sensores, maquina de estados, actuadores y MQTT.
#
# QUE ES ESTE ARCHIVO
# -------------------
# Es el **director de la orquesta**. La FSM (`fsm.py`) decide, los sensores
# miden y los actuadores actuan; este archivo los hace trabajar juntos y ademas
# publica todo por MQTT.
#
# COMO ESTA ORGANIZADO (mapa rapido)
# ----------------------------------
#     Controlador
#     |-- __init__            guarda las piezas y los contadores
#     |-- _ahora / uptime_s   reloj y tiempo encendido
#     |-- _publicar / _evento / _telemetria / _ack   lo que sale por MQTT
#     |-- _aplicar            convierte "efectos" de la FSM en GPIO + eventos
#     |-- _detectar_cambio_estado   avisa cuando cambia de estado
#     |-- _marcar_presencia / _resolver_presencia   no perder una intrusion
#     |-- _ciclo              el corazon: leer, decidir, actuar
#     |-- procesar_comando    atiende ordenes (MQTT, panel, pulsador)
#     |-- _bucle_*            tareas de fondo que corren para siempre
#
# POR QUE TAREAS ASINCRONAS
# -------------------------
# MicroPython en el ESP32 ejecuta **una sola cosa a la vez** (no hay hilos).
# Si el programa se quedara esperando al WiFi, no leería el PIR ni atendería el
# botón. La solucion son las tareas cooperativas de `asyncio`: cada bucle hace
# un pedacito de trabajo, y cuando llega a un `await` (esperar red, esperar
# tiempo) le devuelve el control a las demas. Por eso **nunca** hay un
# `time.sleep` largo adentro de un bucle: se usa `await asyncio.sleep(...)`.
#
#     _bucle_sensores   cada 50 ms: lee sensores y corre la FSM
#     _bucle_leds       cada 100 ms: parpadeo de LEDs y tono de la sirena
#     _bucle_pantalla   cada 600 ms: redibuja el OLED
#     _bucle_telemetria cada 5 s: publica por MQTT
#     _bucle_comandos   espera ordenes que llegaron por el bus
#     _bucle_boton      cada 20 ms: mira el pulsador
#     _bucle_mqtt       conecta, se suscribe y reintenta si se cae
#     _bucle_latido     cada 10 s: imprime un latido para diagnostico
#
# EL PATRON DE "EFECTOS"
# ----------------------
# La FSM no enciende nada: devuelve una lista de efectos como
# `[{"e": "sirena_on"}, {"e": "registrar_alerta", ...}]`. `_aplicar()` recorre
# esa lista y hace lo que corresponde. Asi la logica de seguridad se prueba sin
# hardware y aca queda todo lo que toca pines, JSON y red.

import asyncio
import json
import time

import config
import hal
import fsm as fsm_mod
from bus import Bus

# En MicroPython no todas las versiones tienen `CancelledError`; si no existe,
# queda `()` y el `except` no atrapa nada (sirve igual).
_CANCELADO = getattr(asyncio, "CancelledError", ())

# Lista blanca de ordenes aceptadas: cualquier otra se rechaza y se registra.
# Nunca se ejecuta un comando arbitrario que llegue por la red.
COMANDOS_VALIDOS = ("arm", "disarm", "mute", "unlock", "ping", "set_config")


def reloj_monotonico():
    # Reloj del nodo: segundos con resolucion de milisegundos.
    #
    #     En el ESP32 `time.time()` devuelve segundos **enteros**: con esa
    #     resolucion los periodos de muestreo de 0,15 s (PIR) y 0,5 s (HC-SR04) se
    #     redondeaban a 1 s, y la cuenta regresiva saltaba de segundo en segundo.
    #     `time.ticks_ms()` cuenta milisegundos desde el arranque.
    #
    #     `getattr(..., None)` devuelve None si la funcion no existe (CPython puro):
    #     en ese caso se usa `time.time()` para que las pruebas no se rompan.
    ticks = getattr(time, "ticks_ms", None)
    if ticks is None:          # CPython sin los dobles de las pruebas
        return time.time()
    return ticks() / 1000.0


# Rangos aceptados para el cambio de umbrales en caliente.
# `set_config` permite cambiar umbrales por MQTT sin reiniciar el nodo, pero
# solo dentro de estos limites: un valor absurdo (por ejemplo una distancia de
# alarma de 5000 cm) dejaria la alarma sin efecto.
_LIMITES_CONFIG = {
    "dist_alarm_cm": (10.0, 350.0),
    "exit_delay_s": (0.0, 300.0),
    "temp_alarm_c": (10.0, 120.0),
    "auto_relock_s": (1.0, 120.0),
    "siren_max_s": (5.0, 900.0),
}


class Controlador:
    # Orquestador del nodo de seguridad.

    def __init__(self, cfg, wifi, cliente, sensores, panel, pantalla, maquina,
                 log=None, reloj=None, boton=True):
        # Las piezas llegan ya construidas ("inyeccion de dependencias"):
        # asi el mismo controlador se usa con hardware real o con dobles en
        # las pruebas, sin cambiar una linea.
        self.cfg = cfg
        self.wifi = wifi
        self.cliente = cliente
        self.sensores = sensores
        self.panel = panel
        self.pantalla = pantalla
        self.maquina = maquina
        self._log = log or (lambda mensaje: None)
        self._reloj = reloj or reloj_monotonico

        # Bus interno: el callback de MQTT (sincrono) deja los comandos aca y
        # `_bucle_comandos` los procesa cuando puede.
        self.bus = Bus()
        self._buzon = self.bus.suscribir("cmd")
        self.tareas = []

        # Contadores que van en la telemetria.
        self.seq = 0
        self.eventos = 0
        self.iniciado_en = None
        self.ultimo_estado = maquina.estado
        self.ultimo_telemetria = 0.0
        self._origen_comando = None      # de donde vino la ultima orden

        # Pulsador. `pull_up()` deja el pin en 1 cuando nadie lo aprieta, asi
        # apretar lo baja a 0 (el otro extremo del boton va a GND).
        self._boton = hal.entrada(cfg.PIN_BUTTON, pull=hal.pull_up()) if boton else None
        self._boton_apretado = None      # se adopta en la 1a lectura estable
        self._nivel_boton = None         # ultimo nivel leido (para la traza)
        self._ms_boton = 0               # instante de la ultima pulsacion valida
        self.latido_s = getattr(cfg, "LATIDO_S", 10.0)
        self._ms_led = 0                 # instante del ultimo cambio de LED
        self._ms_sirena = 0              # instante del ultimo cambio de tono
        self._fase_sirena = False        # false = tono bajo, true = tono alto
        self._led_rojo_on = False
        self._led_verde_on = False
        # Niveles anteriores: sirven para detectar el FLANCO (el momento en
        # que el sensor pasa de 0 a 1), no el nivel sostenido.
        self._movimiento_prev = False
        self._distancia_dentro = False
        # Presencia detectada que la FSM todavia no puede atender (cuenta
        # regresiva de salida); se resuelve al quedar ARMADO.
        self._presencia_pendiente = False
        self._pendiente_motivo = "movimiento"
        self._pendiente_cm = None

    # -- utilidades --------------------------------------------------------
    def _ahora(self):
        # Instante actual en segundos (todo el controlador usa este reloj).
        return self._reloj()

    def uptime_s(self):
        # Segundos desde que arranco el controlador.
        if self.iniciado_en is None:
            return 0
        return int(self._ahora() - self.iniciado_en)

    async def _publicar(self, topico, datos, qos=0, retain=False):
        # Publica en MQTT sin romper nada si no hay conexion.
        #
        #         Si `datos` es un diccionario se convierte a JSON; si ya es texto o
        #         bytes se manda tal cual. Devuelve False si no hay broker o si falla.
        if not self.cliente.conectado:
            return False
        try:
            if not isinstance(datos, (str, bytes)):
                datos = json.dumps(datos)
            return await self.cliente.publicar(topico, datos, qos, retain)
        except Exception as exc:  # noqa: BLE001
            self._log("no se pudo publicar en %s: %s" % (topico, exc))
            return False

    async def _evento(self, tipo, severidad, mensaje, extra=None):
        # Publica un evento del sistema (contrato comun con el backend).
        #
        #         Campos: version del protocolo, dispositivo, tipo (`kind`), gravedad
        #         (`severity`), mensaje legible, uptime y estado de la FSM. `extra` es
        #         un diccionario opcional con datos propios del evento.
        self.eventos += 1
        datos = {
            "v": self.cfg.PROTOCOL_VERSION,
            "device": self.cfg.DEVICE_ID,
            "kind": tipo,
            "severity": severidad,
            "message": mensaje,
            "uptime_s": self.uptime_s(),
            "state": self.maquina.estado,
        }
        if extra:
            datos["data"] = extra
        # QoS 1: los eventos no se pueden perder.
        return await self._publicar(self.cfg.TOPIC_EVENTS, datos, qos=1)

    def _telemetria(self):
        # Arma el mensaje periodico con las lecturas y el estado.
        lect = self.sensores.instantanea()
        clima = lect.get("clima") or {}
        resumen = self.maquina.resumen()
        self.seq += 1
        return {
            "v": self.cfg.PROTOCOL_VERSION,
            "device": self.cfg.DEVICE_ID,
            "name": self.cfg.DEVICE_NAME,
            "seq": self.seq,               # numero de mensaje (detecta huecos)
            "uptime_s": self.uptime_s(),
            "temp_c": clima.get("temp_c"),
            "hum_pct": clima.get("hum_pct"),
            "lux": lect.get("luz"),
            "dist_cm": lect.get("distancia"),
            "motion": bool(lect.get("movimiento")),
            "state": resumen["state"],
            "alarm": resumen["alarming"],
            "siren": resumen["siren"],
            "locked": resumen["locked"],
            "alerts": resumen["alerts"],
            "rssi": self.wifi.rssi(),
            "sensor_errors": self.sensores.total_errores(),
            "fw": self.cfg.FIRMWARE_VERSION,
        }

    async def _publicar_telemetria(self):
        # Publica la telemetria (QoS 0: si se pierde una, viene otra en 5 s).
        self.ultimo_telemetria = self._ahora()
        return await self._publicar(self.cfg.TOPIC_TELEMETRY, self._telemetria(),
                                    qos=0)

    # -- aplicacion de efectos --------------------------------------------
    async def _aplicar(self, efectos):
        # Ejecuta la lista de efectos que devolvio la FSM.
        #
        #         Cada rama hace dos cosas: actua sobre el hardware y deja constancia
        #         (traza en el monitor serie + evento por MQTT). El `elif` compara el
        #         campo `e` del efecto con las constantes de `fsm.py`.
        for fx in efectos:
            clase = fx.get("e")

            if clase == fsm_mod.FX_SIRENA_ON:
                # Arranca en el tono bajo; el bucle de LEDs la hara bitonal.
                self.panel.buzzer.encender(self.cfg.SIREN_FREQ_LOW)
                motivo = fx.get("motivo")
                texto = "Sirena activada" + (" (%s)" % motivo if motivo else "")
                self._log(texto)
                await self._evento("alarm", "critical", texto,
                                   {"reason": motivo})

            elif clase == fsm_mod.FX_SIRENA_OFF:
                self.panel.buzzer.apagar()
                motivo = fx.get("motivo")
                texto = "Sirena silenciada" + (" (%s)" % motivo if motivo else "")
                self._log(texto)
                await self._evento("alarm_off", "warning", texto)

            elif clase == fsm_mod.FX_ABRIR:
                self.panel.cerradura.abrir()
                self._log("cerradura abierta (se cierra sola en %ss)"
                          % fx.get("auto_cierre_s"))
                await self._evento("unlock", "warning",
                                   "Cerradura abierta",
                                   {"auto_relock_s": fx.get("auto_cierre_s")})

            elif clase == fsm_mod.FX_CERRAR:
                self.panel.cerradura.cerrar()
                self._log("cerradura cerrada (%s)" % fx.get("motivo"))
                await self._evento("lock", "info", "Cerradura cerrada",
                                   {"reason": fx.get("motivo")})

            elif clase == fsm_mod.FX_ALERTA:
                # Ojo: aca NO se enciende la sirena; eso lo hace FX_SIRENA_ON.
                await self._evento("intrusion", "critical",
                                   "Alerta: %s" % fx.get("motivo", "intrusion"),
                                   {"cm": fx.get("cm"), "c": fx.get("c"),
                                    "alerts": self.maquina.alertas})

            elif clase == fsm_mod.FX_AVISO:
                await self._evento("state", "info",
                                   "Estado: %s" % fx.get("motivo", ""),
                                   {"reason": fx.get("motivo"),
                                    "c": fx.get("c")})

            elif clase == fsm_mod.FX_RECHAZO:
                self._log("comando rechazado: %s (%s)"
                          % (fx.get("cmd"), fx.get("motivo")))
                await self._evento("command_rejected", "warning",
                                   "Comando rechazado: %s" % fx.get("motivo", ""),
                                   {"cmd": fx.get("cmd"),
                                    "reason": fx.get("motivo")})

    async def _detectar_cambio_estado(self):
        # Deja traza y publica un evento SOLO si el estado cambio de verdad.
        #
        #         Comparar con `self.ultimo_estado` evita llenar el log de mensajes
        #         repetidos en cada ciclo (el ciclo corre 20 veces por segundo).
        if self.maquina.estado == self.ultimo_estado:
            return
        anterior = self.ultimo_estado
        self.ultimo_estado = self.maquina.estado
        self._log("estado %s -> %s (%s%s)"
                  % (anterior, self.maquina.estado, self.maquina.ultimo_motivo,
                     (" desde " + self._origen_comando)
                     if self._origen_comando else ""))
        await self._evento("state", "info",
                           "Cambio de estado %s -> %s" % (anterior, self.maquina.estado),
                           {"from": anterior, "to": self.maquina.estado,
                            "reason": self.maquina.ultimo_motivo})

    # -- presencia, ciclo de sensores y seguridad -------------------------
    def _marcar_presencia(self, motivo, cm=None):
        # Anota una presencia detectada por flanco de subida.
        #
        #         Si el sistema esta desarmado se descarta (fue el propio usuario). Si
        #         esta en la cuenta regresiva de salida, la FSM todavia no alerta: antes
        #         ese flanco se perdia para siempre y el PIR parecia no funcionar. Ahora
        #         queda pendiente hasta que el sistema quede ARMADO.
        if self.maquina.estado == fsm_mod.DESARMADO:
            return
        self._presencia_pendiente = True
        self._pendiente_motivo = motivo
        self._pendiente_cm = cm

    def _resolver_presencia(self, ahora):
        # Entrega la presencia pendiente en cuanto la FSM puede alertar.
        #
        #         Devuelve los efectos de la FSM (lista vacia si todavia no corresponde).
        if not self._presencia_pendiente:
            return []
        if self.maquina.estado == fsm_mod.DESARMADO:
            self._presencia_pendiente = False
            return []
        if self.maquina.estado == fsm_mod.ARMANDO:
            return []               # se resuelve al cumplir la cuenta regresiva

        evento = {"type": "presence", "motivo": self._pendiente_motivo}
        if self._pendiente_cm is not None:
            evento["cm"] = self._pendiente_cm
        self._presencia_pendiente = False
        return self.maquina.handle(ahora, evento)

    async def _ciclo(self, ahora):
        # Un paso del sistema de seguridad (corre cada 50 ms).
        #
        #         Orden de las operaciones:
        #           1. leer los sensores que vencieron su periodo,
        #           2. dejar que la FSM resuelva sus temporizadores (`tick`),
        #           3. detectar FLANCOS (no niveles) de movimiento y de distancia,
        #           4. resolver una presencia que quedo pendiente,
        #           5. pasar la temperatura a la FSM,
        #           6. aplicar todos los efectos juntos y avisar si cambio el estado.
        nuevas = self.sensores.actualizar(ahora)
        efectos = self.maquina.tick(ahora)
        distancia_alarma = getattr(self.cfg, "DIST_ALARM_CM", 80.0)

        # Solo se evalua el flanco de subida: el sensor puede quedarse en alto
        # varios segundos (Wokwi lo deja 5 s) y no debe generar una alerta por
        # cada muestra. El antirrebote fino lo hace la FSM (cooldown_alerta_s).
        movimiento = nuevas.get("movimiento")
        if movimiento is not None:
            if movimiento and not self._movimiento_prev:
                self._marcar_presencia("movimiento")
            self._movimiento_prev = bool(movimiento)

        distancia = nuevas.get("distancia")
        if distancia is not None:
            dentro = distancia <= distancia_alarma
            if dentro and not self._distancia_dentro:
                self._marcar_presencia("presencia_cercana", cm=distancia)
            self._distancia_dentro = dentro

        efectos += self._resolver_presencia(ahora)

        clima = nuevas.get("clima") or {}
        if clima.get("temp_c") is not None:
            efectos += self.maquina.handle(
                ahora, {"type": "temperature", "c": clima["temp_c"]}
            )

        if efectos:
            await self._aplicar(efectos)
        await self._detectar_cambio_estado()
        return nuevas

    # -- comandos ----------------------------------------------------------
    def _al_recibir(self, topico, payload, qos, retain):
        # Callback sincrono del cliente MQTT: solo publica en el bus.
        #
        #         Es sincrono porque lo llama la tarea de lectura del socket; el trabajo
        #         pesado (parsear, validar, actuar) lo hace `_bucle_comandos`.
        if topico == self.cfg.TOPIC_COMMAND:
            if retain:
                # Un comando retenido es una orden vieja que el broker repite
                # en cada conexion: si se aceptara, el nodo se armaria solo
                # (o se desarmaria solo) en cada reinicio.
                self._log("comando retenido ignorado: %r" % (payload,))
                return
            # Traza del motivo del armado: sin esto, un `arm` ajeno en el
            # topico publico parecia "el nodo se arma solo".
            self._log("comando MQTT recibido: %r" % (payload,))
            self.bus.publicar("cmd", payload)
        elif topico == self.cfg.TOPIC_CONFIG:
            try:
                datos = json.loads(payload)
            except Exception:  # noqa: BLE001
                self._log("config invalida recibida")
                return
            # Se reenvuelve como un set_config comun para no duplicar codigo.
            self.bus.publicar("cmd", {"id": None, "cmd": "set_config",
                                      "args": datos, "source": "mqtt_config"})

    def _aplicar_config(self, args):
        # Cambia umbrales en caliente, validando clave y rango.
        #
        #         Solo acepta las claves de `_LIMITES_CONFIG`. Devuelve dos
        #         diccionarios: `applied` (lo que se aplico) y `rejected` (motivo del
        #         rechazo), que viajan en el ACK.
        aplicados = {}
        rechazados = {}
        for clave, valor in (args or {}).items():
            limites = _LIMITES_CONFIG.get(clave)
            if limites is None:
                rechazados[clave] = "desconocido"
                continue
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                rechazados[clave] = "no_numerico"
                continue
            minimo, maximo = limites
            if numero < minimo or numero > maximo:
                rechazados[clave] = "fuera_de_rango"
                continue
            if clave == "exit_delay_s":
                self.maquina.salida_s = numero
            elif clave == "auto_relock_s":
                self.maquina.auto_cierre_s = numero
            elif clave == "siren_max_s":
                self.maquina.sirena_max_s = numero
            elif clave == "dist_alarm_cm":
                self.maquina.dist_alarma_cm = numero
                self.cfg.DIST_ALARM_CM = numero
            elif clave == "temp_alarm_c":
                self.maquina.temp_alarma_c = numero
            aplicados[clave] = numero
        return {"applied": aplicados, "rejected": rechazados}

    async def _ack(self, cid, cmd, ok, resultado=None, motivo=None, origen=None):
        # Respuesta al emisor de un comando.
        #
        #         El backend espera este ACK para marcar la orden como OK, RECHAZADO o
        #         TIMEOUT (si no llega en 8 s). `cid` es el id que mando el backend.
        datos = {
            "v": self.cfg.PROTOCOL_VERSION,
            "device": self.cfg.DEVICE_ID,
            "id": cid,
            "cmd": cmd,
            "ok": bool(ok),
            "state": self.maquina.estado,
            "locked": self.maquina.cerrada,
            "alerts": self.maquina.alertas,
            "uptime_s": self.uptime_s(),
        }
        if motivo:
            datos["reason"] = motivo
        if resultado is not None:
            datos["result"] = resultado
        if origen:
            datos["source"] = origen
        return await self._publicar(self.cfg.TOPIC_ACK, datos, qos=1)

    async def procesar_comando(self, crudo):
        # Procesa un comando (bytes JSON o diccionario). Devuelve el ACK.
        #
        #         1. Acepta bytes/str (lo que llega de MQTT) o un diccionario ya armado
        #            (lo que arma el pulsador o el panel).
        #         2. Valida que el comando este en la lista blanca.
        #         3. `ping` y `set_config` se resuelven aca; el resto va a la FSM.
        if isinstance(crudo, (bytes, bytearray, str)):
            try:
                mensaje = json.loads(crudo)
            except Exception:  # noqa: BLE001
                await self._evento("command_rejected", "warning",
                                   "Comando con JSON invalido")
                return None
        else:
            mensaje = crudo

        if not isinstance(mensaje, dict):
            await self._evento("command_rejected", "warning",
                               "Comando sin objeto JSON")
            return None

        cid = mensaje.get("id")
        # `str(...).lower()` normaliza: "ARM" y "arm" son la misma orden.
        cmd = str(mensaje.get("cmd", "")).lower()
        args = mensaje.get("args") or {}
        origen = mensaje.get("source", "mqtt")

        if cmd not in COMANDOS_VALIDOS:
            await self._ack(cid, cmd, False, motivo="comando_no_permitido",
                            origen=origen)
            await self._evento("command_rejected", "warning",
                               "Comando no permitido: %s" % cmd, {"cmd": cmd})
            return False

        if cmd == "ping":
            # Sirve para saber si el nodo esta vivo y cuanto lleva encendido.
            await self._ack(cid, cmd, True, {"pong": self.uptime_s()}, origen=origen)
            return True

        if cmd == "set_config":
            resultado = self._aplicar_config(args)
            await self._ack(cid, cmd, True, resultado, origen=origen)
            await self._evento("config", "info", "Configuracion actualizada",
                               resultado)
            await self._publicar_telemetria()
            return True

        # El resto son ordenes de la FSM (arm, disarm, mute, unlock).
        evento = {"type": "command", "cmd": cmd, "source": origen}
        if cmd == "unlock":
            # El PIN puede venir dentro de args o al mismo nivel del mensaje.
            evento["pin"] = args.get("pin", mensaje.get("pin"))

        rechazo = None
        self._origen_comando = origen
        efectos = self.maquina.handle(self._ahora(), evento)
        for fx in efectos:
            if fx.get("e") == fsm_mod.FX_RECHAZO:
                rechazo = fx.get("motivo")
        await self._aplicar(efectos)
        await self._detectar_cambio_estado()

        ok = rechazo is None
        await self._ack(cid, cmd, ok, motivo=rechazo, origen=origen)
        await self._evento("command", "info" if ok else "warning",
                           "Comando %s %s" % (cmd, "ejecutado" if ok else "rechazado"),
                           {"cmd": cmd, "ok": ok, "reason": rechazo,
                            "source": origen})
        await self._publicar_telemetria()
        return ok

    async def alternar_armado(self, origen="boton"):
        # Un toque del pulsador: arma si estaba desarmado, desarma si no.
        cmd = "disarm" if self.maquina.armado() else "arm"
        return await self.procesar_comando({"id": None, "cmd": cmd,
                                            "args": {}, "source": origen})

    # -- tareas ------------------------------------------------------------
    async def _bucle_sensores(self):
        # El bucle mas importante: cada 50 ms corre un ciclo de seguridad.
        #
        #         El `try/except` es a proposito: si un sensor lanza un error raro, se
        #         anota y **el bucle sigue**. Un fallo de lectura no puede apagar el
        #         sistema de seguridad.
        while True:
            ahora = self._ahora()
            try:
                await self._ciclo(ahora)
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("ciclo de sensores con error: %s" % exc)
            await asyncio.sleep(self.cfg.LOOP_TICK_S)

    async def _bucle_telemetria(self):
        # Publica la telemetria cada `TELEMETRY_PERIOD_S` (5 s).
        while True:
            await asyncio.sleep(self.cfg.TELEMETRY_PERIOD_S)
            try:
                await self._publicar_telemetria()
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("telemetria con error: %s" % exc)

    async def _bucle_comandos(self):
        # Espera ordenes del bus y las procesa de a una.
        #
        #         `await self._buzon.get()` duerme la tarea hasta que el callback de MQTT
        #         (o el pulsador) deja algo: no consume CPU mientras espera.
        while True:
            evento = await self._buzon.get()
            try:
                await self.procesar_comando(evento.get("datos"))
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("comando con error: %s" % exc)

    async def _bucle_leds(self):
        # Patrones de LED y tono bitonal de la sirena (cada 100 ms).
        #
        #         No usa `sleep` por estado: mira el reloj y decide, asi puede atender
        #         varias cosas (LED + sirena) en la misma pasada.
        intervalo = 0.1
        while True:
            ahora_ms = time.ticks_ms()
            estado = self.maquina.estado
            rojo = self.panel.led_rojo
            verde = self.panel.led_verde

            if estado == fsm_mod.ALARMA:
                # Rojo intermitente a 2 Hz (un cambio cada 250 ms).
                if time.ticks_diff(ahora_ms, self._ms_led) >= 250:
                    self._ms_led = ahora_ms
                    rojo.alternar()
                verde.apagar()

            elif estado == fsm_mod.ARMANDO:
                # Verde rapido: avisa que corre la cuenta regresiva.
                if time.ticks_diff(ahora_ms, self._ms_led) >= 125:
                    self._ms_led = ahora_ms
                    verde.alternar()
                rojo.apagar()

            elif estado == fsm_mod.ARMADO:
                rojo.apagar()
                verde.encender()

            else:
                # DISARMED: verde fijo (el sistema esta listo, no vigilando).
                rojo.apagar()
                verde.encender()

            # Tono bitonal de la sirena: alterna dos frecuencias cada 300 ms.
            if self.maquina.sonando:
                if time.ticks_diff(ahora_ms, self._ms_sirena) >= self.cfg.SIREN_TOGGLE_MS:
                    self._ms_sirena = ahora_ms
                    self._fase_sirena = not self._fase_sirena
                    frecuencia = (self.cfg.SIREN_FREQ_HIGH if self._fase_sirena
                                  else self.cfg.SIREN_FREQ_LOW)
                    self.panel.buzzer.encender(frecuencia)
            elif self.panel.buzzer.activo:
                # Si la FSM dejo de sonar, se asegura de apagar el buzzer.
                self.panel.buzzer.apagar()

            await asyncio.sleep(intervalo)

    async def _bucle_pantalla(self):
        # Redibuja el OLED cada `OLED_PERIOD_S` (0,6 s).
        while True:
            try:
                self.pantalla.mostrar(self.datos_pantalla())
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("pantalla con error: %s" % exc)
            await asyncio.sleep(self.cfg.OLED_PERIOD_S)

    async def _bucle_boton(self):
        # Sondea el pulsador y confirma el nivel con dos muestras seguidas.
        #
        #         El sondeo es rapido (20 ms) a proposito: `_bucle_sensores` bloquea el
        #         bucle de eventos hasta ~100 ms cuando mide el HC-SR04, y con el sondeo
        #         anterior (50 ms) un clic corto se perdia. El estado inicial se adopta
        #         sin contarlo como pulsacion: si el pin arranca en 0 el nodo no se arma
        #         solo.
        #
        #         `muestras` cuenta lecturas consecutivas iguales: exigir 2 evita tomar
        #         como pulsacion un ruido de una sola lectura.
        if self._boton is None:
            return
        estable = None
        muestras = 0
        while True:
            try:
                valor = self._boton.value()
                ahora_ms = time.ticks_ms()
                if valor == estable:
                    muestras += 1
                else:
                    estable = valor
                    muestras = 1
                if muestras >= 2:
                    if estable != self._nivel_boton:
                        # Traza que falta cuando "el boton no hace nada": si
                        # esta linea no aparece, el pin no se esta leyendo.
                        self._log("boton nivel %d" % estable)
                        self._nivel_boton = estable
                    if self._boton_apretado is None:
                        # Primera lectura estable: se adopta como estado.
                        self._boton_apretado = estable == 0
                    elif estable == 0 and not self._boton_apretado:
                        self._boton_apretado = True
                        # Antirrebote: dos pulsaciones muy juntas = una sola.
                        if (time.ticks_diff(ahora_ms, self._ms_boton)
                                > self.cfg.BUTTON_DEBOUNCE_MS):
                            self._ms_boton = ahora_ms
                            self._log("boton: pulsacion")
                            await self.alternar_armado("boton")
                    elif estable == 1:
                        self._boton_apretado = False
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("boton con error: %s" % exc)
            await asyncio.sleep(self.cfg.BUTTON_POLL_S)

    async def _bucle_latido(self):
        # Imprime el estado y el nivel del pulsador cada `latido_s`.
        #
        #         Sirve para saber si el bucle de eventos sigue vivo y que esta viendo en
        #         GPIO4, aunque el broker no responda: la seguridad no depende de la red.
        while True:
            await asyncio.sleep(self.latido_s)
            try:
                nivel = self._boton.value() if self._boton is not None else "-"
                self._log("latido estado=%s boton=%s mqtt=%s alertas=%d"
                          % (self.maquina.estado, nivel,
                             "ok" if self.cliente.conectado else "sin",
                             self.maquina.alertas))
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("latido con error: %s" % exc)

    async def _bucle_mqtt(self):
        # Conecta al broker, se suscribe y reintenta si la conexion se cae.
        #
        #         Pasos de cada vuelta: conectar (con LWT `offline`) -> suscribirse a
        #         `cmd` y `config` a QoS 1 -> publicar `online` retenido -> avisar por
        #         eventos -> esperar a que se caiga (`esperar_caida`). Cuando se cae,
        #         espera 2 s (y despues 4, 8... hasta 60) antes de reintentar.
        espera = self.cfg.MQTT_RECONNECT_MIN_S
        while True:
            try:
                await self.cliente.conectar(self.cfg.TOPIC_STATUS, "offline")
                self.cliente.on_message = self._al_recibir
                await self.cliente.suscribir([
                    (self.cfg.TOPIC_COMMAND, 1),
                    (self.cfg.TOPIC_CONFIG, 1),
                ])
                espera = self.cfg.MQTT_RECONNECT_MIN_S
                # Retenido: quien se conecte despues sabe que estamos online.
                await self._publicar(self.cfg.TOPIC_STATUS, "online", qos=1,
                                     retain=True)
                await self._evento("network", "info", "MQTT conectado")
                await self._publicar_telemetria()
                await self.cliente.esperar_caida()
            except _CANCELADO:
                raise
            except Exception as exc:  # noqa: BLE001
                self._log("fallo de conexion MQTT: %s" % exc)

            await self._evento("network", "warning",
                               "MQTT desconectado; reintento en %ds" % espera)
            await asyncio.sleep(espera)
            # Backoff exponencial con tope: 2, 4, 8, 16, 32, 60, 60...
            espera = min(self.cfg.MQTT_RECONNECT_MAX_S, espera * 2)

    def datos_pantalla(self):
        # Arma el diccionario que consume `display.Pantalla.mostrar`.
        lect = self.sensores.instantanea()
        clima = lect.get("clima") or {}
        restante = self.maquina.restante_salida(self._ahora())
        return {
            "state": self.maquina.estado,
            "temp_c": clima.get("temp_c"),
            "hum_pct": clima.get("hum_pct"),
            "lux": lect.get("luz"),
            "dist_cm": lect.get("distancia"),
            "motion": bool(lect.get("movimiento")),
            "alerts": self.maquina.alertas,
            "siren": self.maquina.sonando,
            "locked": self.maquina.cerrada,
            "rssi": self.wifi.rssi(),
            "mqtt": self.cliente.conectado,
            # `int(restante)` redondea hacia abajo los segundos que faltan.
            "arm_in_s": int(restante) if restante else 0,
            "exit_delay": self.maquina.salida_s,
        }

    async def ejecutar(self):
        # Arranca todas las tareas cooperativas y espera indefinidamente.
        #
        #         `asyncio.create_task` programa cada bucle para que corra "en paralelo"
        #         (cooperativamente) y `asyncio.gather` espera a todas. Como ninguna
        #         termina nunca, esta corrutina dura hasta que el programa se detiene.
        self.iniciado_en = self._ahora()
        self._log("controlador iniciado: %s" % self.cfg.DEVICE_NAME)
        self.pantalla.aviso("Iniciando...")
        self.tareas = [
            asyncio.create_task(self._bucle_mqtt()),
            asyncio.create_task(self._bucle_sensores()),
            asyncio.create_task(self._bucle_telemetria()),
            asyncio.create_task(self._bucle_leds()),
            asyncio.create_task(self._bucle_pantalla()),
            asyncio.create_task(self._bucle_comandos()),
            asyncio.create_task(self._bucle_latido()),
        ]
        if self._boton is not None:
            self.tareas.append(asyncio.create_task(self._bucle_boton()))
        await asyncio.gather(*self.tareas)

    async def detener(self):
        # Apagado ordenado: cancela tareas, cierra MQTT y apaga actuadores.
        #
        #         `tarea.cancel()` hace que el `await` en el que este dormida cada tarea
        #         lance `CancelledError` y termine. Despues se cierra el socket y se
        #         apagan LEDs y buzzer para no dejar el nodo "sonando solo".
        for tarea in self.tareas:
            tarea.cancel()
        self.tareas = []
        try:
            await self.cliente.cerrar()
        except Exception:  # noqa: BLE001
            pass
        self.panel.apagar_todo()
