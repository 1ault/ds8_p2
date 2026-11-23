"""Maquina de estados de seguridad: logica pura, sin hardware ni red.

QUE ES UNA MAQUINA DE ESTADOS
-----------------------------
Es un programa que en cada momento esta en **un** estado de una lista corta, y
que solo cambia de estado cuando pasa algo que corresponde. El ejemplo clasico
es un semaforo: verde -> amarillo -> rojo, y no puede saltar de verde a rojo.

Aca los estados son cuatro:

    DISARMED  sistema desactivado, la cerradura puede abrirse con PIN
    ARMING    cuenta regresiva de salida antes de armar
    ARMED     vigilando: cualquier presencia dispara la alarma
    ALARM     alarma activa hasta que se desarme o se silencie

y las transiciones posibles son:

    DISARMED --(orden "arm")--> ARMING --(pasan 10 s)--> ARMED
    ARMING   --(orden "disarm")-> DISARMED
    ARMED    --(presencia o calor)--> ALARM
    ALARM    --(orden "disarm")-> DISARMED          (apaga la sirena)
    ALARM    --(orden "mute")----> ALARM silenciada  (sigue en alarma)

POR QUE ESTE ARCHIVO NO TOCA EL HARDWARE
----------------------------------------
Porque asi se puede probar **entero** sin placas: cada evento devuelve una
lista de *efectos* ("que hay que hacer") y el controlador (`app.py`) es el que
los convierte en GPIO, MQTT o mensajes. Si la FSM encendiera el LED por su
cuenta, habria que simular un ESP32 para probar una simple transicion.

    fsm.handle(ahora, {"type": "presence"})
    -> [{"e": "registrar_alerta", ...}, {"e": "sirena_on"}]

Los "efectos" son diccionarios con la clave `"e"` (de "efecto") y los datos
que necesite cada uno.

COMO SE MIDEN LOS TIEMPOS
-------------------------
La FSM no tiene reloj propio: cada llamada recibe `ahora` (segundos). Los
temporizadores se guardan como **fecha de vencimiento** (`_fin_armado = ahora +
10`) y `tick()` los compara con el nuevo `ahora`. Asi no hay `sleep` adentro:
el paso del tiempo lo aporta quien llama.
"""

# Estados
DESARMADO = "DISARMED"
ARMANDO = "ARMING"
ARMADO = "ARMED"
ALARMA = "ALARM"

ESTADOS = (DESARMADO, ARMANDO, ARMADO, ALARMA)

# Efectos que el controlador debe ejecutar
FX_SIRENA_ON = "sirena_on"
FX_SIRENA_OFF = "sirena_off"
FX_CERRAR = "cerrar_cerradura"
FX_ABRIR = "abrir_cerradura"
FX_ALERTA = "registrar_alerta"
FX_AVISO = "registrar_aviso"
FX_RECHAZO = "rechazar_comando"


def _fx(nombre, **datos):
    """Arma un efecto: `{"e": nombre}` + los datos que vengan.

    `**datos` junta todos los argumentos con nombre en un diccionario, asi
    `_fx(FX_AVISO, motivo="armed")` devuelve
    `{"e": "registrar_aviso", "motivo": "armed"}`.
    """
    efecto = {"e": nombre}
    efecto.update(datos)
    return efecto


class SecurityFSM:
    """Maquina de estados con temporizadores basados en tiempo del llamador."""

    def __init__(self, salida_s=10, auto_cierre_s=8, sirena_max_s=120,
                 dist_alarma_cm=80.0, temp_alarma_c=45.0, pin="2468",
                 intentos_pin=3, bloqueo_pin_s=30, cooldown_alerta_s=5.0):
        self.salida_s = salida_s
        self.auto_cierre_s = auto_cierre_s
        self.sirena_max_s = sirena_max_s
        self.dist_alarma_cm = dist_alarma_cm
        self.temp_alarma_c = temp_alarma_c
        self.pin = pin
        self.intentos_pin = intentos_pin
        self.bloqueo_pin_s = bloqueo_pin_s
        self.cooldown_alerta_s = cooldown_alerta_s

        # Estado actual y datos que viajan en la telemetria.
        self.estado = DESARMADO
        self.cerrada = True          # la cerradura arranca cerrada
        self.sonando = False         # sirena encendida
        self.silenciada = False      # se pulso "mute" en esta alarma
        self.alertas = 0             # cuantas intrusiones se contaron
        self.ultimo_motivo = ""      # por que paso lo ultimo (va al evento)

        # Temporizadores: guardan el instante en que vencen (None = apagado).
        self._fin_armado = None      # fin de la cuenta regresiva de salida
        self._fin_sirena = None      # limite de duracion de la sirena
        self._fin_bloqueo = None     # fin del bloqueo por PIN fallido
        self._fin_rearme = None      # cierre automatico de la cerradura
        self._fallos_pin = 0         # intentos de PIN incorrectos seguidos
        self._ultima_alerta = None   # instante de la ultima alerta (cooldown)

    # -- consultas ---------------------------------------------------------
    def armado(self):
        """True en los tres estados "vigilando" (ARMING, ARMED y ALARM)."""
        return self.estado in (ARMANDO, ARMADO, ALARMA)

    def en_alarma(self):
        return self.estado == ALARMA

    def restante_salida(self, ahora):
        """Segundos que faltan para que termine la cuenta regresiva."""
        if self._fin_armado is None:
            return 0.0
        restante = self._fin_armado - ahora
        # Nunca devuelve negativo: si ya vencio, quedan 0.
        return restante if restante > 0 else 0.0

    def resumen(self):
        """Diccionario con el estado para la telemetria y la pantalla."""
        return {
            "state": self.estado,
            "locked": self.cerrada,
            "alarming": self.estado == ALARMA,
            "siren": self.sonando,
            "muted": self.silenciada,
            "alerts": self.alertas,
            "last_reason": self.ultimo_motivo,
        }

    # -- eventos externos --------------------------------------------------
    def handle(self, ahora, evento):
        """Procesa un evento. Devuelve la lista de efectos a ejecutar.

        `evento` es un diccionario con `"type"`: "command", "presence" o
        "temperature". Cualquier otro tipo se ignora (devuelve lista vacia).
        """
        tipo = evento.get("type", "")

        if tipo == "command":
            return self._comando(ahora, evento)

        if tipo == "presence":
            return self._presencia(ahora, evento)

        if tipo == "temperature":
            return self._temperatura(ahora, evento)

        return []

    def tick(self, ahora):
        """Avance del reloj: resuelve temporizadores vencidos.

        Es lo unico que "deja pasar el tiempo". Se llama desde el ciclo de
        seguridad cada 50 ms.
        """
        efectos = []

        # 1) termino la cuenta regresiva: el sistema queda ARMADO.
        if self.estado == ARMANDO and self._fin_armado is not None:
            if ahora >= self._fin_armado:
                self.estado = ARMADO
                self._fin_armado = None
                self.ultimo_motivo = "exit_delay_done"
                efectos.append(_fx(FX_AVISO, motivo="armed"))

        # 2) Vencio el bloqueo por PIN: se limpian los intentos fallidos.
        if self._fin_bloqueo is not None and ahora >= self._fin_bloqueo:
            self._fin_bloqueo = None
            self._fallos_pin = 0

        # 3) Cierre automatico de la cerradura despues de abrirla.
        if self._fin_rearme is not None and ahora >= self._fin_rearme:
            self._fin_rearme = None
            if not self.cerrada:
                self.cerrada = True
                efectos.append(_fx(FX_CERRAR, motivo="auto_relock"))

        return efectos

    # -- comandos ----------------------------------------------------------
    def _comando(self, ahora, evento):
        """Ordenes que llegan de MQTT, del panel o del pulsador."""
        cmd = evento.get("cmd", "")
        efectos = []

        if cmd == "arm":
            # Solo se arma si estaba desarmado (armar dos veces no reinicia
            # la cuenta regresiva).
            if self.estado == DESARMADO:
                self.estado = ARMANDO
                self._fin_armado = ahora + self.salida_s
                self.silenciada = False
                self.ultimo_motivo = "arm"
                if not self.cerrada:
                    self.cerrada = True
                    efectos.append(_fx(FX_CERRAR, motivo="arm"))
                efectos.append(_fx(FX_AVISO, motivo="arming"))
            return efectos

        if cmd == "disarm":
            era_alarma = self.estado == ALARMA
            self.estado = DESARMADO
            self._fin_armado = None
            self.silenciada = False
            self.ultimo_motivo = "disarm"
            if self.sonando:
                self.sonando = False
                self._fin_sirena = None
                efectos.append(_fx(FX_SIRENA_OFF, motivo="disarm"))
            if not self.cerrada:
                self.cerrada = True
                efectos.append(_fx(FX_CERRAR, motivo="disarm"))
            efectos.append(_fx(FX_AVISO, motivo="disarmed",
                               alarma_previa=era_alarma))
            return efectos

        if cmd == "mute":
            # Silencia esta alarma; una alerta nueva vuelve a sonar.
            if self.estado == ALARMA:
                self.silenciada = True
                if self.sonando:
                    self.sonando = False
                    self._fin_sirena = None
                    efectos.append(_fx(FX_SIRENA_OFF, motivo="mute"))
            return efectos

        if cmd == "unlock":
            return self._abrir(ahora, evento)

        # Cualquier otra orden se rechaza y queda registrada.
        efectos.append(_fx(FX_RECHAZO, cmd=cmd, motivo="desconocido"))
        return efectos

    def _abrir(self, ahora, evento):
        """Abrir la cerradura con PIN. Tres controles antes de abrir."""
        if self.estado != DESARMADO:
            # Con el sistema armado/vigilando no se abre desde afuera.
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="sistema_armado")]

        if self._fin_bloqueo is not None and ahora < self._fin_bloqueo:
            # Todavia dura el castigo por los PIN errados.
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="bloqueado")]

        if evento.get("pin") != self.pin:
            self._fallos_pin += 1
            if self._fallos_pin >= self.intentos_pin:
                # Se llego al maximo: bloqueo por `bloqueo_pin_s` segundos.
                self._fallos_pin = 0
                self._fin_bloqueo = ahora + self.bloqueo_pin_s
                return [_fx(FX_RECHAZO, cmd="unlock", motivo="pin_bloqueado")]
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="pin_incorrecto")]

        # PIN correcto: abre y programa el cierre automatico.
        self._fallos_pin = 0
        self.cerrada = False
        self._fin_rearme = ahora + self.auto_cierre_s
        self.ultimo_motivo = "unlock"
        return [_fx(FX_ABRIR, auto_cierre_s=self.auto_cierre_s)]

    # -- sensores ----------------------------------------------------------
    def _puede_alertar(self, ahora):
        """Antirrebote: evita contar la misma intrusion muchas veces seguidas.

        Si paso menos de `cooldown_alerta_s` desde la ultima alerta, devuelve
        False. Sin esto, un movimiento de 5 s generaria decenas de alertas.
        """
        if self._ultima_alerta is None:
            return True
        return (ahora - self._ultima_alerta) >= self.cooldown_alerta_s

    def _presencia(self, ahora, evento):
        """Alguien aparecio: movimiento del PIR o distancia chica del HC-SR04."""
        if self.estado not in (ARMADO, ALARMA):
            # Si esta desarmado o en la cuenta regresiva, no se alerta (el
            # controlador se encarga de no perder la presencia en ese caso).
            return []
        if not self._puede_alertar(ahora):
            return []

        distancia = evento.get("cm")
        motivo = evento.get("motivo", "movimiento")
        if distancia is not None:
            motivo = "presencia_cercana"

        self._ultima_alerta = ahora
        self.alertas += 1
        self.estado = ALARMA
        self.ultimo_motivo = motivo
        efectos = [_fx(FX_ALERTA, motivo=motivo, cm=distancia)]

        # Una alerta nueva vuelve a sonar aunque la anterior se haya silenciado.
        self.silenciada = False
        self.sonando = True
        self._fin_sirena = ahora + self.sirena_max_s
        efectos.append(_fx(FX_SIRENA_ON))

        return efectos

    def _temperatura(self, ahora, evento):
        """Sobrecalentamiento: segunda fuente de deteccion, sin movimiento."""
        celsius = evento.get("c")
        if celsius is None:
            return []
        if celsius < self.temp_alarma_c:
            return []

        if self.estado not in (ARMADO, ALARMA):
            # Desarmado no es una intrusion: solo se deja un aviso.
            return [_fx(FX_AVISO, motivo="temperatura_alta", c=celsius)]

        if not self._puede_alertar(ahora):
            return []

        self._ultima_alerta = ahora
        self.alertas += 1
        self.estado = ALARMA
        self.ultimo_motivo = "sobrecalentamiento"
        efectos = [_fx(FX_ALERTA, motivo="sobrecalentamiento", c=celsius)]
        # Una alerta nueva vuelve a sonar aunque la anterior se haya silenciado.
        self.silenciada = False
        self.sonando = True
        self._fin_sirena = ahora + self.sirena_max_s
        efectos.append(_fx(FX_SIRENA_ON))
        return efectos


def crear_desde_config(cfg):
    """Construye la FSM a partir del modulo de configuracion."""
    return SecurityFSM(
        salida_s=cfg.EXIT_DELAY_S,
        auto_cierre_s=cfg.AUTO_RELOCK_S,
        sirena_max_s=cfg.SIREN_MAX_S,
        dist_alarma_cm=cfg.DIST_ALARM_CM,
        temp_alarma_c=cfg.TEMP_ALARM_C,
        pin=cfg.UNLOCK_PIN,
        intentos_pin=cfg.PIN_INTENTOS_MAX,
        bloqueo_pin_s=cfg.PIN_BLOQUEO_S,
    )
