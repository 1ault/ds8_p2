"""Configuracion del backend, leida del entorno (o de un archivo .env).

Todos los valores tienen un default util para la demostracion local: sin
configurar nada el backend arranca, guarda en SQLite y sirve el panel. La nube
(ThingSpeak) solo se activa si hay claves.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _leer_env(ruta: Path) -> None:
    """Carga un .env sencillo sin depender de python-dotenv."""
    try:
        from dotenv import load_dotenv

        if ruta.exists():
            load_dotenv(ruta, override=False)
            return
    except ImportError:
        pass

    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(clave, valor)


def _texto(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto).strip()


def _entero(nombre: str, defecto: int) -> int:
    try:
        return int(os.environ.get(nombre, "").strip() or defecto)
    except ValueError:
        return defecto


def _flotante(nombre: str, defecto: float) -> float:
    try:
        return float(os.environ.get(nombre, "").strip() or defecto)
    except ValueError:
        return defecto


def _booleano(nombre: str, defecto: bool = False) -> bool:
    valor = os.environ.get(nombre, "").strip().lower()
    if not valor:
        return defecto
    return valor in ("1", "true", "yes", "si", "sí", "on")


@dataclass(frozen=True)
class Config:
    """Instantanea de la configuracion del backend."""

    # Servidor web
    host: str = "127.0.0.1"
    puerto: int = 8000
    secreto: str = "cambia-este-secreto-en-produccion"
    usuario: str = "admin"
    clave: str = "seguridad2026"
    sin_login: bool = False
    debug: bool = False

    # Base de datos
    ruta_bd: Path = RAIZ / "data" / "centinela.db"
    dias_retencion: int = 30

    # MQTT
    mqtt_host: str = "broker.hivemq.com"
    mqtt_puerto: int = 1883
    mqtt_tls: bool = False
    mqtt_usuario: str = ""
    mqtt_clave: str = ""
    mqtt_prefijo: str = "centinela"
    device_id: str = "dev01"
    mqtt_timeout_ack_s: float = 8.0

    # Nube (ThingSpeak)
    ts_canal: str = ""
    ts_write_key: str = ""
    ts_read_key: str = ""
    ts_talkback_id: str = ""
    ts_talkback_key: str = ""
    ts_intervalo_s: float = 20.0
    ts_talkback_intervalo_s: float = 15.0

    # Demo
    auto_arranque_demo: bool = False

    @property
    def base_topicos(self) -> str:
        return "%s/%s" % (self.mqtt_prefijo, self.device_id)

    @property
    def topico_telemetria(self) -> str:
        return self.base_topicos + "/telemetry"

    @property
    def topico_eventos(self) -> str:
        return self.base_topicos + "/events"

    @property
    def topico_estado(self) -> str:
        return self.base_topicos + "/status"

    @property
    def topico_comando(self) -> str:
        return self.base_topicos + "/cmd"

    @property
    def topico_ack(self) -> str:
        return self.base_topicos + "/ack"

    @property
    def topico_config(self) -> str:
        return self.base_topicos + "/config"

    @property
    def topico_suscripcion(self) -> str:
        return "%s/+/#" % self.mqtt_prefijo

    @property
    def nube_activa(self) -> bool:
        return bool(self.ts_canal and self.ts_write_key)

    @property
    def talkback_activo(self) -> bool:
        return bool(self.ts_talkback_id and self.ts_talkback_key)

    def con(self, **cambios) -> "Config":
        """Devuelve una copia con cambios (util en pruebas)."""
        return replace(self, **cambios)


def cargar(ruta_env: Path | None = None, usar_entorno: bool = True) -> Config:
    """Construye la configuracion desde el entorno (y el .env si existe)."""
    if usar_entorno:
        _leer_env(ruta_env or (RAIZ / ".env"))

    ruta_bd = _texto("DB_PATH", "") or str(RAIZ / "data" / "centinela.db")
    return Config(
        host=_texto("WEB_HOST", "127.0.0.1"),
        puerto=_entero("WEB_PORT", 8000),
        secreto=_texto("SECRET_KEY", "cambia-este-secreto-en-produccion"),
        usuario=_texto("WEB_USER", "admin"),
        clave=_texto("WEB_PASSWORD", "seguridad2026"),
        sin_login=_booleano("SIN_LOGIN", False),
        debug=_booleano("DEBUG", False),
        ruta_bd=Path(ruta_bd),
        dias_retencion=_entero("RETENTION_DAYS", 30),
        mqtt_host=_texto("MQTT_HOST", "broker.hivemq.com"),
        mqtt_puerto=_entero("MQTT_PORT", 1883),
        mqtt_tls=_booleano("MQTT_TLS", False),
        mqtt_usuario=_texto("MQTT_USER", ""),
        mqtt_clave=_texto("MQTT_PASSWORD", ""),
        mqtt_prefijo=_texto("TOPIC_PREFIX", "centinela"),
        device_id=_texto("DEVICE_ID", "dev01"),
        mqtt_timeout_ack_s=_flotante("MQTT_ACK_TIMEOUT_S", 8.0),
        ts_canal=_texto("THINGSPEAK_CHANNEL", ""),
        ts_write_key=_texto("THINGSPEAK_WRITE_KEY", ""),
        ts_read_key=_texto("THINGSPEAK_READ_KEY", ""),
        ts_talkback_id=_texto("THINGSPEAK_TALKBACK_ID", ""),
        ts_talkback_key=_texto("THINGSPEAK_TALKBACK_KEY", ""),
        ts_intervalo_s=_flotante("THINGSPEAK_INTERVAL_S", 20.0),
        ts_talkback_intervalo_s=_flotante("TALKBACK_INTERVAL_S", 15.0),
        auto_arranque_demo=_booleano("DEMO", False),
    )
