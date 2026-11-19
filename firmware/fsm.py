"""Maquina de estados de seguridad: logica pura, sin hardware ni red.

Estados
-------
DISARMED  sistema desactivado, la cerradura puede abrirse con PIN
ARMING    cuenta regresiva de salida antes de armar
ARMED     vigilando: cualquier presencia dispara la alarma
ALARM     alarma activa hasta que se desarme o se silencie

El resultado de cada transicion es una lista de efectos ("que hay que hacer")
que el controlador traduce a acciones sobre LEDs, sirena, cerradura y MQTT.
Asi la logica se prueba entera sin simular GPIO.
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

        self.estado = DESARMADO
        self.cerrada = True
        self.sonando = False
        self.silenciada = False
        self.alertas = 0
        self.ultimo_motivo = ""

        self._fin_armado = None
        self._fin_sirena = None
        self._fin_bloqueo = None
        self._fin_rearme = None
        self._fallos_pin = 0
        self._ultima_alerta = None

    # -- consultas ---------------------------------------------------------
    def armado(self):
        return self.estado in (ARMANDO, ARMADO, ALARMA)

    def en_alarma(self):
        return self.estado == ALARMA

    def restante_salida(self, ahora):
        if self._fin_armado is None:
            return 0.0
        restante = self._fin_armado - ahora
        return restante if restante > 0 else 0.0

    def resumen(self):
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
        """Procesa un evento. Devuelve la lista de efectos a ejecutar."""
        tipo = evento.get("type", "")

        if tipo == "command":
            return self._comando(ahora, evento)

        if tipo == "presence":
            return self._presencia(ahora, evento)

        if tipo == "temperature":
            return self._temperatura(ahora, evento)

        return []

    def tick(self, ahora):
        """Avance del reloj: resuelve temporizadores vencidos."""
        efectos = []

        if self.estado == ARMANDO and self._fin_armado is not None:
            if ahora >= self._fin_armado:
                self.estado = ARMADO
                self._fin_armado = None
                self.ultimo_motivo = "exit_delay_done"
                efectos.append(_fx(FX_AVISO, motivo="armed"))

        if self._fin_bloqueo is not None and ahora >= self._fin_bloqueo:
            self._fin_bloqueo = None
            self._fallos_pin = 0

        if self._fin_rearme is not None and ahora >= self._fin_rearme:
            self._fin_rearme = None
            if not self.cerrada:
                self.cerrada = True
                efectos.append(_fx(FX_CERRAR, motivo="auto_relock"))

        return efectos

    # -- comandos ----------------------------------------------------------
    def _comando(self, ahora, evento):
        cmd = evento.get("cmd", "")
        efectos = []

        if cmd == "arm":
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

        efectos.append(_fx(FX_RECHAZO, cmd=cmd, motivo="desconocido"))
        return efectos

    def _abrir(self, ahora, evento):
        if self.estado != DESARMADO:
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="sistema_armado")]

        if self._fin_bloqueo is not None and ahora < self._fin_bloqueo:
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="bloqueado")]

        if evento.get("pin") != self.pin:
            self._fallos_pin += 1
            if self._fallos_pin >= self.intentos_pin:
                self._fallos_pin = 0
                self._fin_bloqueo = ahora + self.bloqueo_pin_s
                return [_fx(FX_RECHAZO, cmd="unlock", motivo="pin_bloqueado")]
            return [_fx(FX_RECHAZO, cmd="unlock", motivo="pin_incorrecto")]

        self._fallos_pin = 0
        self.cerrada = False
        self._fin_rearme = ahora + self.auto_cierre_s
        self.ultimo_motivo = "unlock"
        return [_fx(FX_ABRIR, auto_cierre_s=self.auto_cierre_s)]

    # -- sensores ----------------------------------------------------------
    def _puede_alertar(self, ahora):
        """Antirrebote: evita contar la misma intrusion muchas veces seguidas."""
        if self._ultima_alerta is None:
            return True
        return (ahora - self._ultima_alerta) >= self.cooldown_alerta_s

    def _presencia(self, ahora, evento):
        if self.estado not in (ARMADO, ALARMA):
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
        celsius = evento.get("c")
        if celsius is None:
            return []
        if celsius < self.temp_alarma_c:
            return []

        if self.estado not in (ARMADO, ALARMA):
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
