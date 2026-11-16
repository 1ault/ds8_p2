"""Acceso a datos sobre SQLite (asincrono, con un unico escritor).

Todas las consultas usan parametros (`?`), nunca concatenacion de cadenas. La
conexion vive en un hilo del pool y el acceso se serializa con un lock
asincrono: SQLite no admite escrituras concurrentes y asi se evita el clasico
`database is locked`.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ESQUEMA = RAIZ / "sql" / "schema.sql"


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """Texto ISO-8601 en UTC con sufijo Z (ordenable como cadena)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def a_epoch(dt: datetime) -> float:
    return dt.timestamp()


def desde_epoch(valor: float) -> datetime:
    return datetime.fromtimestamp(valor, tz=timezone.utc)


class Almacen:
    """DAO de lecturas, eventos, comandos y cambios de estado."""

    def __init__(self, ruta: Path | str, ruta_esquema: Path | None = None,
                 reloj=None):
        self.ruta = Path(ruta)
        self.ruta_esquema = Path(ruta_esquema) if ruta_esquema else RUTA_ESQUEMA
        self._reloj = reloj or ahora_utc
        self._conn: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self.escrituras = 0

    # -- ciclo de vida -----------------------------------------------------
    def _crear_conexion(self) -> sqlite3.Connection:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.ruta), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    async def abrir(self) -> "Almacen":
        """Crea la conexion y aplica el esquema (idempotente)."""
        if self._conn is not None:
            return self
        esquema = self.ruta_esquema.read_text(encoding="utf-8")
        self._conn = self._crear_conexion()
        self._conn.executescript(esquema)
        self._conn.commit()
        return self

    async def cerrar(self) -> None:
        if self._conn is None:
            return
        conn, self._conn = self._conn, None
        await asyncio.to_thread(self._cerrar_hilo, conn)

    @staticmethod
    def _cerrar_hilo(conn: sqlite3.Connection) -> None:
        try:
            conn.commit()
        finally:
            conn.close()

    async def _leer(self, consulta: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        async with self._lock:
            return await asyncio.to_thread(self._filas, consulta, tuple(params))

    def _filas(self, consulta: str, params: tuple) -> list[sqlite3.Row]:
        conn = self._requerir()
        return conn.execute(consulta, params).fetchall()

    async def _escribir(self, consulta: str, params: Iterable[Any] = ()) -> int:
        """Ejecuta un INSERT y devuelve el rowid generado."""
        async with self._lock:
            return await asyncio.to_thread(self._ejecutar_escritura, consulta, tuple(params))

    async def _actualizar(self, consulta: str, params: Iterable[Any] = ()) -> int:
        """Ejecuta un UPDATE/DELETE y devuelve cuantas filas cambio."""
        async with self._lock:
            return await asyncio.to_thread(self._ejecutar_actualizacion, consulta, tuple(params))

    def _ejecutar_escritura(self, consulta: str, params: tuple) -> int:
        conn = self._requerir()
        cur = conn.execute(consulta, params)
        conn.commit()
        self.escrituras += 1
        return cur.lastrowid or 0

    def _ejecutar_actualizacion(self, consulta: str, params: tuple) -> int:
        conn = self._requerir()
        cur = conn.execute(consulta, params)
        conn.commit()
        self.escrituras += 1
        return cur.rowcount or 0

    def _requerir(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("el almacen no esta abierto")
        return self._conn

    # -- dispositivos ------------------------------------------------------
    async def registrar_dispositivo(self, device_id: str, nombre: str = "",
                                    ubicacion: str = "", firmware: str = "") -> None:
        ahora = self._reloj()
        await self._escribir(
            """INSERT INTO devices (device_id, nombre, ubicacion, firmware, creado_utc, visto_utc, visto_epoch)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(device_id) DO UPDATE SET
                   visto_utc = excluded.visto_utc,
                   visto_epoch = excluded.visto_epoch,
                   nombre = CASE WHEN excluded.nombre <> '' THEN excluded.nombre ELSE devices.nombre END,
                   ubicacion = CASE WHEN excluded.ubicacion <> '' THEN excluded.ubicacion ELSE devices.ubicacion END,
                   firmware = CASE WHEN excluded.firmware <> '' THEN excluded.firmware ELSE devices.firmware END""",
            (device_id, nombre or device_id, ubicacion, firmware, iso(ahora),
             iso(ahora), a_epoch(ahora)),
        )

    async def dispositivos(self) -> list[dict]:
        filas = await self._leer("SELECT * FROM devices ORDER BY device_id")
        return [dict(f) for f in filas]

    async def _asegurar_dispositivo(self, device_id: str) -> None:
        """Garantiza la fila del dispositivo (respetando la clave foranea).

        Se llama antes de guardar lecturas, eventos, comandos o cambios de
        estado para que el orden de llamadas no importe.
        """
        ahora = self._reloj()
        await self._escribir(
            """INSERT OR IGNORE INTO devices
                   (device_id, nombre, creado_utc, visto_utc, visto_epoch)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, device_id, iso(ahora), iso(ahora), a_epoch(ahora)),
        )

    # -- lecturas ----------------------------------------------------------
    async def guardar_lectura(self, device_id: str, datos: dict) -> int:
        """Guarda una lectura de sensores con su marca de tiempo del servidor."""
        await self._asegurar_dispositivo(device_id)
        ahora = self._reloj()
        fila = (
            device_id,
            a_epoch(ahora),
            iso(ahora),
            _num(datos.get("temp_c")),
            _num(datos.get("hum_pct")),
            _num(datos.get("lux")),
            _num(datos.get("dist_cm")),
            1 if datos.get("motion") else 0,
            str(datos.get("state") or "DESCONOCIDO"),
            1 if datos.get("alarm") else 0,
            1 if datos.get("siren") else 0,
            1 if datos.get("locked", True) else 0,
            _ent(datos.get("alerts"), 0),
            _ent(datos.get("rssi")),
            _ent(datos.get("seq")),
            _ent(datos.get("sensor_errors"), 0),
            json.dumps(datos, ensure_ascii=False, separators=(",", ":")),
        )
        return await self._escribir(
            """INSERT INTO readings (device_id, ts_epoch, ts_utc, temp_c, hum_pct, lux,
                                     dist_cm, motion, state, alarm, siren, locked, alerts,
                                     rssi, seq, sensor_errors, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            fila,
        )

    async def ultima_lectura(self, device_id: str) -> dict | None:
        filas = await self._leer(
            "SELECT * FROM readings WHERE device_id = ? ORDER BY ts_epoch DESC LIMIT 1",
            (device_id,),
        )
        return dict(filas[0]) if filas else None

    async def historico(self, device_id: str, horas: float = 6.0,
                        limite: int = 500) -> list[dict]:
        desde = a_epoch(self._reloj() - timedelta(hours=horas))
        filas = await self._leer(
            """SELECT ts_epoch, ts_utc, temp_c, hum_pct, lux, dist_cm, motion,
                      state, alarm, alerts
                 FROM readings
                WHERE device_id = ? AND ts_epoch >= ?
                ORDER BY ts_epoch DESC
                LIMIT ?""",
            (device_id, desde, limite),
        )
        return [dict(f) for f in reversed(filas)]

    async def agregado_horario(self, device_id: str, horas: float = 24.0) -> list[dict]:
        desde = a_epoch(self._reloj() - timedelta(hours=horas))
        filas = await self._leer(
            """SELECT CAST(ts_epoch / 3600 AS INTEGER) * 3600 AS bucket,
                      COUNT(*)          AS muestras,
                      AVG(temp_c)       AS temp_media,
                      MIN(temp_c)       AS temp_min,
                      MAX(temp_c)       AS temp_max,
                      AVG(hum_pct)      AS hum_media,
                      AVG(lux)          AS lux_media,
                      MIN(dist_cm)      AS dist_min,
                      SUM(alarm)        AS alarmas
                 FROM readings
                WHERE device_id = ? AND ts_epoch >= ?
                GROUP BY bucket
                ORDER BY bucket""",
            (device_id, desde),
        )
        salida = []
        for f in filas:
            fila = dict(f)
            fila["desde_utc"] = iso(desde_epoch(fila["bucket"]))
            salida.append(fila)
        return salida

    # -- eventos -----------------------------------------------------------
    async def registrar_evento(self, device_id: str, kind: str, message: str,
                               severity: str = "info", state: str | None = None,
                               datos: dict | None = None) -> int:
        await self._asegurar_dispositivo(device_id)
        ahora = self._reloj()
        return await self._escribir(
            """INSERT INTO events (device_id, ts_epoch, ts_utc, kind, severity, message, state, data_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_id, a_epoch(ahora), iso(ahora), kind, severity, message, state,
             json.dumps(datos, ensure_ascii=False, separators=(",", ":")) if datos else None),
        )

    async def eventos(self, device_id: str, limite: int = 50,
                      severidad: str | None = None) -> list[dict]:
        if severidad:
            filas = await self._leer(
                """SELECT * FROM events WHERE device_id = ? AND severity = ?
                    ORDER BY ts_epoch DESC LIMIT ?""",
                (device_id, severidad, limite),
            )
        else:
            filas = await self._leer(
                "SELECT * FROM events WHERE device_id = ? ORDER BY ts_epoch DESC LIMIT ?",
                (device_id, limite),
            )
        return [_con_datos(f) for f in filas]

    # -- comandos ----------------------------------------------------------
    async def crear_comando(self, cmd_id: str, device_id: str, cmd: str,
                            args: dict | None, source: str) -> None:
        await self._asegurar_dispositivo(device_id)
        ahora = self._reloj()
        await self._escribir(
            """INSERT INTO commands (id, device_id, cmd, args_json, source, estado,
                                     emitido_epoch, emitido_utc)
               VALUES (?, ?, ?, ?, ?, 'PENDIENTE', ?, ?)""",
            (cmd_id, device_id, cmd,
             json.dumps(args or {}, ensure_ascii=False, separators=(",", ":")),
             source or "panel", a_epoch(ahora), iso(ahora)),
        )

    async def confirmar_comando(self, cmd_id: str, estado: str,
                                resultado: dict | None = None,
                                motivo: str | None = None) -> bool:
        ahora = self._reloj()
        fila = await self._leer(
            "SELECT emitido_epoch FROM commands WHERE id = ?", (cmd_id,)
        )
        if not fila:
            return False
        latencia = int(max(0.0, a_epoch(ahora) - fila[0]["emitido_epoch"]) * 1000)
        cambiadas = await self._actualizar(
            """UPDATE commands
                  SET estado = ?, confirmado_epoch = ?, confirmado_utc = ?,
                      latencia_ms = ?, resultado_json = ?, motivo = ?
                WHERE id = ? AND estado = 'PENDIENTE'""",
            (estado, a_epoch(ahora), iso(ahora), latencia,
             json.dumps(resultado, ensure_ascii=False, separators=(",", ":")) if resultado else None,
             motivo, cmd_id),
        )
        return cambiadas > 0

    async def expirar_comandos(self, timeout_s: float) -> int:
        """Marca como TIMEOUT los comandos sin confirmar."""
        limite = a_epoch(self._reloj() - timedelta(seconds=timeout_s))
        async with self._lock:
            return await asyncio.to_thread(self._expirar_hilo, limite)

    def _expirar_hilo(self, limite: float) -> int:
        conn = self._requerir()
        cur = conn.execute(
            """UPDATE commands SET estado = 'TIMEOUT', motivo = 'sin_ack'
                WHERE estado = 'PENDIENTE' AND emitido_epoch <= ?""",
            (limite,),
        )
        conn.commit()
        self.escrituras += 1
        return cur.rowcount or 0

    async def comandos(self, limite: int = 25) -> list[dict]:
        filas = await self._leer(
            "SELECT * FROM commands ORDER BY emitido_epoch DESC LIMIT ?", (limite,)
        )
        salida = []
        for f in filas:
            fila = dict(f)
            fila["args"] = _json(fila.pop("args_json", None))
            fila["resultado"] = _json(fila.pop("resultado_json", None))
            salida.append(fila)
        return salida

    async def estado_comandos(self) -> dict:
        filas = await self._leer(
            "SELECT estado, COUNT(*) AS n FROM commands GROUP BY estado"
        )
        return {f["estado"]: f["n"] for f in filas}

    # -- cambios de estado -------------------------------------------------
    async def registrar_cambio_estado(self, device_id: str, desde: str | None,
                                      hacia: str, motivo: str | None = None) -> int:
        await self._asegurar_dispositivo(device_id)
        ahora = self._reloj()
        return await self._escribir(
            """INSERT INTO state_changes (device_id, ts_epoch, ts_utc, desde, hacia, motivo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (device_id, a_epoch(ahora), iso(ahora), desde, hacia, motivo),
        )

    async def cambios_estado(self, device_id: str, limite: int = 20) -> list[dict]:
        filas = await self._leer(
            """SELECT * FROM state_changes WHERE device_id = ?
                ORDER BY ts_epoch DESC LIMIT ?""",
            (device_id, limite),
        )
        return [dict(f) for f in filas]

    # -- estadisticas y mantenimiento --------------------------------------
    async def estadisticas(self, device_id: str) -> dict:
        lecturas = await self._leer(
            """SELECT COUNT(*) AS total, MIN(ts_epoch) AS primera, MAX(ts_epoch) AS ultima,
                      AVG(temp_c) AS temp_media, MIN(temp_c) AS temp_min, MAX(temp_c) AS temp_max,
                      AVG(hum_pct) AS hum_media, MIN(dist_cm) AS dist_min,
                      SUM(alarm) AS alarmas, MAX(alerts) AS alertas_max
                 FROM readings WHERE device_id = ?""",
            (device_id,),
        )
        eventos = await self._leer(
            """SELECT severity, COUNT(*) AS n FROM events WHERE device_id = ?
                GROUP BY severity""",
            (device_id,),
        )
        comandos = await self._leer(
            """SELECT estado, COUNT(*) AS n, AVG(latencia_ms) AS latencia
                 FROM commands WHERE device_id = ? GROUP BY estado""",
            (device_id,),
        )
        resumen = dict(lecturas[0]) if lecturas else {}
        resumen["eventos_por_severidad"] = {f["severity"]: f["n"] for f in eventos}
        resumen["comandos_por_estado"] = {f["estado"]: f["n"] for f in comandos}
        latencias = [f["latencia"] for f in comandos if f["latencia"] is not None]
        resumen["latencia_media_ms"] = round(sum(latencias) / len(latencias), 1) if latencias else None
        return resumen

    async def purgar(self, dias: int) -> dict:
        """Borra datos mas antiguos que `dias` (mantenimiento)."""
        limite = a_epoch(self._reloj() - timedelta(days=dias))
        async with self._lock:
            return await asyncio.to_thread(self._purgar_hilo, limite)

    def _purgar_hilo(self, limite: float) -> dict:
        conn = self._requerir()
        lecturas = conn.execute("DELETE FROM readings WHERE ts_epoch < ?", (limite,)).rowcount
        eventos = conn.execute("DELETE FROM events WHERE ts_epoch < ?", (limite,)).rowcount
        comandos = conn.execute("DELETE FROM commands WHERE emitido_epoch < ?", (limite,)).rowcount
        conn.commit()
        self.escrituras += 1
        return {"readings": lecturas or 0, "events": eventos or 0,
                "commands": comandos or 0}


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _num(valor) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _ent(valor, defecto=None):
    if valor is None or valor == "":
        return defecto
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return defecto


def _json(texto):
    if not texto:
        return None
    try:
        return json.loads(texto)
    except (TypeError, ValueError):
        return None


def _con_datos(fila: sqlite3.Row) -> dict:
    datos = dict(fila)
    datos["data"] = _json(datos.pop("data_json", None))
    return datos
