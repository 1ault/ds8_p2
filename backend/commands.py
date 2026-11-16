"""Servicio de comandos: validacion, envio, espera de ACK y auditoria.

Reglas duras:
  * solo se aceptan comandos de la lista blanca;
  * los argumentos se validan por tipo y rango antes de tocar la red;
  * todo comando se guarda en la base *antes* de publicarse;
  * un comando sin ACK se marca TIMEOUT (nunca queda "en el aire");
  * hay un limite de frecuencia por origen para evitar abuso.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from typing import Any

from .config import Config
from .storage import iso, ahora_utc


class Validador:
    """Validacion de comandos y de sus argumentos."""

    COMANDOS = ("arm", "disarm", "mute", "unlock", "ping", "set_config")

    RANGOS_CONFIG = {
        "dist_alarm_cm": (10.0, 350.0),
        "exit_delay_s": (0.0, 300.0),
        "temp_alarm_c": (10.0, 120.0),
        "auto_relock_s": (1.0, 120.0),
        "siren_max_s": (5.0, 900.0),
    }

    LIMITE_ARGS = 512

    def validar(self, cmd: str, args: Any) -> tuple[bool, str | None, dict]:
        """Devuelve (valido, motivo_de_rechazo, argumentos_limpios)."""
        nombre = (cmd or "").strip().lower()
        if nombre not in self.COMANDOS:
            return False, "comando_no_permitido", {}

        if args is None:
            args = {}
        if not isinstance(args, dict):
            return False, "argumentos_invalidos", {}
        try:
            if len(json.dumps(args)) > self.LIMITE_ARGS:
                return False, "argumentos_demasiado_grandes", {}
        except (TypeError, ValueError):
            return False, "argumentos_no_serializables", {}

        if nombre == "unlock":
            pin = str(args.get("pin", "")).strip()
            if not pin.isdigit() or not (4 <= len(pin) <= 8):
                return False, "pin_invalido", {}
            return True, None, {"pin": pin}

        if nombre == "set_config":
            limpio: dict[str, float] = {}
            for clave, valor in args.items():
                if clave not in self.RANGOS_CONFIG:
                    continue
                try:
                    numero = float(valor)
                except (TypeError, ValueError):
                    return False, "config_no_numerica", {}
                minimo, maximo = self.RANGOS_CONFIG[clave]
                if not (minimo <= numero <= maximo):
                    return False, "config_fuera_de_rango", {}
                limpio[clave] = numero
            if not limpio:
                return False, "config_vacia", {}
            return True, None, limpio

        # arm / disarm / mute / ping no llevan argumentos
        return True, None, {}

    def claves_config(self) -> list[str]:
        return list(self.RANGOS_CONFIG)


class ServicioComandos:
    """Orquesta el ciclo de vida de un comando remoto."""

    def __init__(self, cfg: Config, almacen, puente, hub=None, log=None,
                 reloj=None, timeout_s: float | None = None,
                 limite_por_minuto: int = 30):
        self.cfg = cfg
        self.almacen = almacen
        self.puente = puente
        self.hub = hub
        self._log = log or (lambda mensaje: None)
        self._reloj = reloj or ahora_utc
        self.timeout_s = timeout_s if timeout_s is not None else cfg.mqtt_timeout_ack_s
        self._validador = Validador()
        self._pendientes: dict[str, dict] = {}
        self._historial = deque()
        self.limite_por_minuto = limite_por_minuto
        self.aceptados = 0
        self.rechazados = 0
        self.timeouts = 0

    # -- utilidades --------------------------------------------------------
    def _permitir(self, ahora: float) -> bool:
        while self._historial and ahora - self._historial[0] > 60.0:
            self._historial.popleft()
        if len(self._historial) >= self.limite_por_minuto:
            return False
        self._historial.append(ahora)
        return True

    def _publicar_hub(self, datos: dict) -> None:
        if self.hub is not None:
            self.hub.publicar("comando", datos)

    def pendientes(self) -> int:
        return len(self._pendientes)

    # -- envio -------------------------------------------------------------
    async def ejecutar(self, cmd: str, args: Any = None,
                       source: str = "panel") -> dict:
        """Valida, audita y envia un comando. Devuelve el resultado con el ACK."""
        ahora = self._reloj()
        valido, motivo, limpio = self._validador.validar(cmd, args)
        if not valido:
            self.rechazados += 1
            self._publicar_hub({"id": None, "cmd": cmd, "ok": False,
                                "motivo": motivo, "source": source})
            return {"ok": False, "motivo": motivo, "id": None}

        if not self._permitir(ahora.timestamp()):
            self.rechazados += 1
            return {"ok": False, "motivo": "demasiados_comandos", "id": None}

        if not self.puente.conectado:
            self.rechazados += 1
            return {"ok": False, "motivo": "sin_conexion_mqtt", "id": None}

        cmd_id = uuid.uuid4().hex[:12]
        await self.almacen.crear_comando(cmd_id, self.cfg.device_id, cmd, limpio,
                                         source)

        futuro: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pendientes[cmd_id] = {"futuro": futuro, "cmd": cmd, "source": source}

        mensaje = {
            "v": 1,
            "id": cmd_id,
            "cmd": cmd,
            "args": limpio,
            "source": source,
            "ts_utc": iso(ahora),
        }
        enviado = self.puente.publicar(self.cfg.topico_comando, mensaje, qos=1)
        if not enviado:
            self._pendientes.pop(cmd_id, None)
            await self.almacen.confirmar_comando(cmd_id, "ERROR", None,
                                                 "no_se_pudo_publicar")
            self._publicar_hub({"id": cmd_id, "cmd": cmd, "ok": False,
                                "motivo": "publicacion_fallida", "source": source})
            return {"ok": False, "motivo": "publicacion_fallida", "id": cmd_id}

        self.aceptados += 1
        try:
            ack = await asyncio.wait_for(futuro, self.timeout_s)
        except asyncio.TimeoutError:
            self.timeouts += 1
            self._pendientes.pop(cmd_id, None)
            await self.almacen.confirmar_comando(cmd_id, "TIMEOUT", None, "sin_ack")
            self._publicar_hub({"id": cmd_id, "cmd": cmd, "ok": False,
                                "motivo": "timeout", "source": source})
            return {"ok": False, "motivo": "timeout", "id": cmd_id}

        return {
            "ok": bool(ack.get("ok")),
            "id": cmd_id,
            "motivo": ack.get("reason"),
            "ack": ack,
        }

    # -- ACK del dispositivo ----------------------------------------------
    async def confirmar(self, payload: dict) -> bool:
        """Procesa un ACK recibido del nodo y libera la espera."""
        if not isinstance(payload, dict):
            return False
        cmd_id = payload.get("id")
        pendiente = self._pendientes.pop(cmd_id, None)
        if pendiente is None:
            return False

        estado = "OK" if payload.get("ok") else "RECHAZADO"
        await self.almacen.confirmar_comando(
            cmd_id, estado, payload.get("result"), payload.get("reason")
        )
        datos = {
            "id": cmd_id,
            "cmd": pendiente["cmd"],
            "ok": bool(payload.get("ok")),
            "motivo": payload.get("reason"),
            "source": pendiente["source"],
            "state": payload.get("state"),
        }
        self._publicar_hub(datos)

        futuro = pendiente["futuro"]
        if not futuro.done():
            futuro.set_result(payload)
        return True

    async def expirar(self) -> int:
        """Marca TIMEOUT los comandos que ya no pueden recibir ACK."""
        return await self.almacen.expirar_comandos(self.timeout_s)

    def cerrar(self) -> None:
        for pendiente in self._pendientes.values():
            futuro = pendiente["futuro"]
            if not futuro.done():
                futuro.cancel()
        self._pendientes.clear()
