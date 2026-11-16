"""Puente entre paho-mqtt (basado en hilos) y asyncio.

paho-mqtt es la libreria de referencia para MQTT en Python, pero su bucle de
red vive en un hilo propio. Aqui se usa `connect_async` + `loop_start()` para
que arranque sin bloquear, y los callbacks depositan los mensajes en una cola
asincrona con `call_soon_threadsafe`. El resto del backend nunca ve hilos.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any


def _codigo_exitoso(codigo: Any) -> bool:
    """Normaliza el codigo de resultado entre paho 1.x y 2.x."""
    if codigo is None:
        return True
    fallo = getattr(codigo, "is_failure", None)
    if callable(fallo):
        try:
            return not fallo()
        except Exception:  # noqa: BLE001
            pass
    valor = getattr(codigo, "value", codigo)
    try:
        return int(valor) == 0
    except (TypeError, ValueError):
        return str(codigo).lower() in ("success", "0", "normal disconnection")


class PuenteMqtt:
    """Cliente MQTT con una API asincrona sencilla."""

    def __init__(self, cfg, log=None, fabrica_cliente=None):
        self.cfg = cfg
        self._log = log or (lambda mensaje: None)
        self._fabrica = fabrica_cliente
        self._cliente = None
        self._cola: asyncio.Queue = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._listo = asyncio.Event()
        self.conectado = False
        self.recibidos = 0
        self.enviados = 0
        self.ultimo_error: str | None = None

    # -- configuracion -----------------------------------------------------
    def _crear_cliente(self):
        if self._fabrica is not None:
            return self._fabrica()

        import paho.mqtt.client as mqtt

        cliente_id = "centinela-backend-%s" % self.cfg.device_id
        version = getattr(mqtt, "CallbackAPIVersion", None)
        if version is not None:
            cliente = mqtt.Client(version.VERSION2, client_id=cliente_id,
                                  protocol=mqtt.MQTTv311, clean_session=True)
        else:  # paho 1.x
            cliente = mqtt.Client(client_id=cliente_id,
                                  protocol=mqtt.MQTTv311, clean_session=True)
        if self.cfg.mqtt_usuario:
            cliente.username_pw_set(self.cfg.mqtt_usuario, self.cfg.mqtt_clave)
        if self.cfg.mqtt_tls:
            cliente.tls_set()
        return cliente

    def _conectar_callbacks(self) -> None:
        cliente = self._cliente
        cliente.on_connect = self._al_conectar
        cliente.on_disconnect = self._al_desconectar
        cliente.on_message = self._al_recibir
        if hasattr(cliente, "reconnect_delay_set"):
            cliente.reconnect_delay_set(min_delay=2, max_delay=60)

    # -- ciclo de vida -----------------------------------------------------
    async def iniciar(self) -> bool:
        self._loop = asyncio.get_running_loop()
        try:
            self._cliente = self._crear_cliente()
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = "no se pudo crear el cliente MQTT: %s" % exc
            self._log(self.ultimo_error)
            return False

        self._conectar_callbacks()
        try:
            self._cliente.connect_async(self.cfg.mqtt_host, self.cfg.mqtt_puerto,
                                        keepalive=30)
            self._cliente.loop_start()
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = str(exc)
            self._log("fallo al conectar MQTT: %s" % exc)
            return False

        try:
            await asyncio.wait_for(self._listo.wait(), 8)
        except asyncio.TimeoutError:
            self._log("MQTT sin CONNACK en 8s; se sigue reintentando en segundo plano")
        return self.conectado

    async def detener(self) -> None:
        cliente = self._cliente
        self._cliente = None
        self.conectado = False
        if cliente is None:
            return
        try:
            cliente.loop_stop()
        except Exception:  # noqa: BLE001
            pass
        try:
            cliente.disconnect()
        except Exception:  # noqa: BLE001
            pass

    # -- callbacks de paho (hilo de red) -----------------------------------
    def _al_conectar(self, *args) -> None:
        # paho 1.x: (cliente, userdata, flags, rc)
        # paho 2.x: (cliente, userdata, flags, reason_code, properties)
        codigo = args[3] if len(args) >= 4 else 0
        ok = _codigo_exitoso(codigo)
        self.conectado = ok
        loop = self._loop
        if loop is None:
            return
        loop.call_soon_threadsafe(self._listo.set)
        if not ok:
            self.ultimo_error = "CONNACK con codigo %s" % (codigo,)
            self._log("MQTT rechazo la conexion: %s" % codigo)
            return
        self._log("MQTT conectado a %s:%d" % (self.cfg.mqtt_host, self.cfg.mqtt_puerto))
        topico = getattr(self.cfg, "topico_suscripcion", None)
        if topico:
            try:
                self._cliente.subscribe(topico, qos=1)
                self._log("suscrito a %s" % topico)
            except Exception as exc:  # noqa: BLE001
                self._log("no se pudo suscribir: %s" % exc)

    def _al_desconectar(self, *args) -> None:
        self.conectado = False
        self._log("MQTT desconectado")
        loop = self._loop
        if loop is not None:
            loop.call_soon_threadsafe(
                self._cola.put_nowait, (None, {"type": "disconnect"})
            )

    def _al_recibir(self, cliente, userdata, mensaje) -> None:
        self.recibidos += 1
        loop = self._loop
        if loop is None:
            return
        datos = {
            "topic": mensaje.topic,
            "payload": bytes(mensaje.payload),
            "qos": mensaje.qos,
            "retain": bool(mensaje.retain),
        }
        loop.call_soon_threadsafe(self._cola.put_nowait, (mensaje.topic, datos))

    # -- API asincrona -----------------------------------------------------
    def publicar(self, topico: str, payload: Any, qos: int = 1,
                 retain: bool = False) -> bool:
        """Publica un mensaje. Devuelve False si no hay conexion."""
        cliente = self._cliente
        if cliente is None:
            return False
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        try:
            info = cliente.publish(topico, payload, qos=qos, retain=retain)
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = str(exc)
            self._log("publicacion fallida: %s" % exc)
            return False
        codigo = getattr(info, "rc", 0)
        if codigo != 0:
            self.ultimo_error = "rc=%s" % codigo
            return False
        self.enviados += 1
        return True

    async def recibir(self) -> tuple[str | None, dict]:
        """Espera el siguiente mensaje: (topico, datos)."""
        return await self._cola.get()

    def estado(self) -> dict:
        return {
            "conectado": self.conectado,
            "host": self.cfg.mqtt_host,
            "puerto": self.cfg.mqtt_puerto,
            "tls": self.cfg.mqtt_tls,
            "recibidos": self.recibidos,
            "enviados": self.enviados,
            "error": self.ultimo_error,
        }


def decodificar(payload: bytes) -> dict | None:
    """Convierte el payload MQTT en diccionario (None si no es JSON)."""
    if not payload:
        return None
    try:
        datos = json.loads(payload.decode("utf-8", "replace"))
    except (ValueError, UnicodeDecodeError):
        return None
    return datos if isinstance(datos, dict) else None
