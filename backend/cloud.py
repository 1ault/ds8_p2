"""Integracion con ThingSpeak: canal de datos (8 campos) y TalkBack.

El backend sube una lectura cada `ts_intervalo_s` (20 s por defecto, el limite
del plan gratuito) y consulta la cola de comandos de TalkBack para traer
ordenes dictadas desde la nube.

Sin claves configuradas, `NubeThingSpeak.activa` es False y todas las
operaciones devuelven False: el sistema funciona igual en local.
"""

from __future__ import annotations

import json
import time
from typing import Any

BASE_THINGSPEAK = "https://api.thingspeak.com"

# Codigos numericos para el campo de estado (ThingSpeak solo maneja numeros)
STATE_CODES = {"DISARMED": 0, "ARMING": 1, "ARMED": 2, "ALARM": 3}


def parsear_comando(texto: str) -> dict | None:
    """Convierte el texto de TalkBack en un comando del sistema.

    Formatos aceptados:
        arm                  -> {"cmd": "arm", "args": {}}
        unlock:2468          -> {"cmd": "unlock", "args": {"pin": "2468"}}
        set_config:dist_alarm_cm=120
    """
    if not texto:
        return None
    limpio = str(texto).strip()
    if not limpio:
        return None

    if ":" not in limpio:
        return {"cmd": limpio.lower(), "args": {}}

    nombre, resto = limpio.split(":", 1)
    nombre = nombre.strip().lower()
    resto = resto.strip()

    if nombre == "unlock":
        return {"cmd": "unlock", "args": {"pin": resto}}

    if nombre == "set_config":
        args: dict[str, float] = {}
        for trozo in resto.split(","):
            if "=" not in trozo:
                continue
            clave, valor = trozo.split("=", 1)
            try:
                args[clave.strip()] = float(valor.strip())
            except ValueError:
                continue
        if not args:
            return None
        return {"cmd": "set_config", "args": args}

    if not resto:
        return {"cmd": nombre, "args": {}}
    return {"cmd": nombre, "args": {}}


class NubeThingSpeak:
    """Cliente del canal de ThingSpeak y de su aplicacion TalkBack."""

    def __init__(self, cfg, sesion=None, reloj=None, log=None,
                 base: str = BASE_THINGSPEAK):
        self.cfg = cfg
        self._sesion = sesion
        self._propia = sesion is None
        self._base = base.rstrip("/")
        self._reloj = reloj or time.time
        self._log = log or (lambda mensaje: None)
        self._ultimo_envio = 0.0

        self.enviados = 0
        self.errores = 0
        self.omitidos = 0
        self.ultimo_entry: str | None = None
        self.comandos_recibidos = 0
        self.ultimo_error: str | None = None

    # -- estado ------------------------------------------------------------
    def activa(self) -> bool:
        return bool(self.cfg.ts_canal and self.cfg.ts_write_key)

    def talkback(self) -> bool:
        return bool(self.cfg.ts_talkback_id and self.cfg.ts_talkback_key)

    def estado(self) -> dict:
        return {
            "activa": self.activa(),
            "talkback": self.talkback(),
            "canal": self.cfg.ts_canal or None,
            "enviados": self.enviados,
            "errores": self.errores,
            "omitidos": self.omitidos,
            "ultimo_entry": self.ultimo_entry,
            "comandos_recibidos": self.comandos_recibidos,
            "error": self.ultimo_error,
        }

    # -- sesion HTTP -------------------------------------------------------
    def _obtener_sesion(self):
        if self._sesion is not None:
            return self._sesion
        import aiohttp

        self._sesion = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )
        return self._sesion

    async def cerrar(self) -> None:
        if self._propia and self._sesion is not None:
            try:
                await self._sesion.close()
            except Exception:  # noqa: BLE001
                pass
        self._sesion = None

    # -- canal de datos ----------------------------------------------------
    def construir_campos(self, lectura: dict) -> dict:
        """Mapea la telemetria a los 8 campos del canal."""
        return {
            "field1": lectura.get("temp_c"),
            "field2": lectura.get("hum_pct"),
            "field3": lectura.get("lux"),
            "field4": lectura.get("dist_cm"),
            "field5": 1 if lectura.get("motion") else 0,
            "field6": 1 if lectura.get("alarm") else 0,
            "field7": STATE_CODES.get(str(lectura.get("state")), -1),
            "field8": lectura.get("alerts", 0),
        }

    async def subir(self, lectura: dict) -> bool:
        """Envia una lectura al canal respetando el intervalo minimo."""
        if not self.activa():
            return False

        ahora = self._reloj()
        if ahora - self._ultimo_envio < self.cfg.ts_intervalo_s:
            self.omitidos += 1
            return False

        datos: dict[str, Any] = {"api_key": self.cfg.ts_write_key}
        datos.update(self.construir_campos(lectura))
        campos = {k: v for k, v in datos.items() if v is not None}

        try:
            sesion = self._obtener_sesion()
            async with sesion.post(self._base + "/update", data=campos) as respuesta:
                texto = (await respuesta.text()).strip()
                if respuesta.status == 200 and texto not in ("0", ""):
                    self._ultimo_envio = ahora
                    self.enviados += 1
                    self.ultimo_entry = texto
                    return True
                self.errores += 1
                self.ultimo_error = "respuesta %s: %s" % (respuesta.status, texto[:80])
                self._log("ThingSpeak rechazo la lectura: %s" % self.ultimo_error)
                return False
        except Exception as exc:  # noqa: BLE001
            self.errores += 1
            self.ultimo_error = str(exc)
            self._log("error subiendo a ThingSpeak: %s" % exc)
            return False

    # -- TalkBack ----------------------------------------------------------
    async def siguiente_comando(self) -> dict | None:
        """Pide a TalkBack el siguiente comando de la cola (si hay)."""
        if not self.talkback():
            return None

        url = "%s/talkbacks/%s/commands/execute.json" % (
            self._base, self.cfg.ts_talkback_id)
        try:
            sesion = self._obtener_sesion()
            async with sesion.get(url, params={"api_key": self.cfg.ts_talkback_key}) as respuesta:
                if respuesta.status != 200:
                    self.ultimo_error = "talkback http %s" % respuesta.status
                    return None
                texto = (await respuesta.text()).strip()
                if not texto or texto in ("-1", "null", "[]"):
                    return None
                datos = json.loads(texto)
                comando = parsear_comando(datos.get("command_string"))
                if comando is None:
                    return None
                comando["talkback_id"] = datos.get("id")
                self.comandos_recibidos += 1
                return comando
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = str(exc)
            self._log("error consultando TalkBack: %s" % exc)
            return None


class NubeNula:
    """Implementacion vacia (patron Null Object) para pruebas y modo local."""

    def activa(self) -> bool:
        return False

    def talkback(self) -> bool:
        return False

    def estado(self) -> dict:
        return {"activa": False, "talkback": False, "canal": None,
                "enviados": 0, "errores": 0, "omitidos": 0,
                "ultimo_entry": None, "comandos_recibidos": 0, "error": None}

    async def subir(self, lectura: dict) -> bool:
        return False

    async def siguiente_comando(self) -> dict | None:
        return None

    async def cerrar(self) -> None:
        return None
