-- =============================================================================
--  Centinela IoT - Esquema de la base de datos (SQLite)
--  Parcial #2 - Desarrollo de Software VIII
--
--  Uso directo:
--      sqlite3 data/centinela.db < sql/schema.sql
--
--  El backend aplica este mismo archivo al arrancar (es idempotente).
--  Marcas de tiempo: ts_epoch (REAL, segundos UTC) para calculos e indices,
--  ts_utc (TEXT ISO-8601 con Z) para lectura humana y exportacion.
-- =============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Dispositivos (nodos ESP32 registrados)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    device_id    TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    ubicacion    TEXT,
    firmware     TEXT,
    creado_utc   TEXT NOT NULL,
    visto_utc    TEXT,
    visto_epoch  REAL
);

-- -----------------------------------------------------------------------------
-- Lecturas de sensores (una fila por mensaje de telemetria)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS readings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id      TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    ts_epoch       REAL NOT NULL,
    ts_utc         TEXT NOT NULL,
    temp_c         REAL,
    hum_pct        REAL,
    lux            REAL,
    dist_cm        REAL,
    motion         INTEGER NOT NULL DEFAULT 0,
    state          TEXT    NOT NULL DEFAULT 'DESCONOCIDO',
    alarm          INTEGER NOT NULL DEFAULT 0,
    siren          INTEGER NOT NULL DEFAULT 0,
    locked         INTEGER NOT NULL DEFAULT 1,
    alerts         INTEGER NOT NULL DEFAULT 0,
    rssi           INTEGER,
    seq            INTEGER,
    sensor_errors  INTEGER NOT NULL DEFAULT 0,
    payload        TEXT,
    CHECK (state IN ('DISARMED', 'ARMING', 'ARMED', 'ALARM', 'DESCONOCIDO')),
    CHECK (motion IN (0, 1)),
    CHECK (alarm IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_readings_device_ts ON readings (device_id, ts_epoch DESC);
CREATE INDEX IF NOT EXISTS idx_readings_alarm     ON readings (alarm, ts_epoch DESC);

-- -----------------------------------------------------------------------------
-- Eventos del sistema (alarmas, cambios de estado, red, comandos)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id  TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    ts_epoch   REAL NOT NULL,
    ts_utc     TEXT NOT NULL,
    kind       TEXT NOT NULL,
    severity   TEXT NOT NULL DEFAULT 'info',
    message    TEXT NOT NULL,
    state      TEXT,
    data_json  TEXT,
    CHECK (severity IN ('info', 'warning', 'critical'))
);

CREATE INDEX IF NOT EXISTS idx_events_device_ts ON events (device_id, ts_epoch DESC);
CREATE INDEX IF NOT EXISTS idx_events_severity  ON events (severity, ts_epoch DESC);

-- -----------------------------------------------------------------------------
-- Comandos enviados al dispositivo, con su confirmacion (ACK)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commands (
    id                TEXT PRIMARY KEY,
    device_id         TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    cmd               TEXT NOT NULL,
    args_json         TEXT,
    source            TEXT,
    estado            TEXT NOT NULL DEFAULT 'PENDIENTE',
    emitido_epoch     REAL NOT NULL,
    emitido_utc       TEXT NOT NULL,
    confirmado_epoch  REAL,
    confirmado_utc    TEXT,
    latencia_ms       INTEGER,
    resultado_json    TEXT,
    motivo            TEXT,
    CHECK (estado IN ('PENDIENTE', 'OK', 'RECHAZADO', 'TIMEOUT', 'ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_commands_emitido ON commands (emitido_epoch DESC);
CREATE INDEX IF NOT EXISTS idx_commands_estado  ON commands (estado);

-- -----------------------------------------------------------------------------
-- Historial de transiciones de la maquina de estados de seguridad
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS state_changes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id  TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    ts_epoch   REAL NOT NULL,
    ts_utc     TEXT NOT NULL,
    desde      TEXT,
    hacia      TEXT NOT NULL,
    motivo     TEXT
);

CREATE INDEX IF NOT EXISTS idx_state_device_ts ON state_changes (device_id, ts_epoch DESC);

-- =============================================================================
-- Vistas
-- =============================================================================

-- Ultima lectura conocida de cada dispositivo
DROP VIEW IF EXISTS v_ultima_lectura;
CREATE VIEW v_ultima_lectura AS
SELECT r.*
  FROM readings r
  JOIN (SELECT device_id, MAX(ts_epoch) AS ultima
          FROM readings
         GROUP BY device_id) u
    ON u.device_id = r.device_id AND u.ultima = r.ts_epoch;

-- Resumen por hora (graficas de tendencia)
DROP VIEW IF EXISTS v_resumen_horario;
CREATE VIEW v_resumen_horario AS
SELECT device_id,
       CAST(ts_epoch / 3600 AS INTEGER) * 3600 AS bucket_epoch,
       COUNT(*)                                AS muestras,
       ROUND(AVG(temp_c), 2)                   AS temp_media,
       ROUND(MIN(temp_c), 2)                   AS temp_min,
       ROUND(MAX(temp_c), 2)                   AS temp_max,
       ROUND(AVG(hum_pct), 2)                  AS hum_media,
       ROUND(AVG(lux), 1)                      AS lux_media,
       ROUND(MIN(dist_cm), 1)                  AS dist_min,
       SUM(alarm)                              AS alarmas,
       SUM(motion)                             AS muestras_movimiento
  FROM readings
 GROUP BY device_id, bucket_epoch;

-- Salud de los comandos por dia y origen
DROP VIEW IF EXISTS v_salud_comandos;
CREATE VIEW v_salud_comandos AS
SELECT device_id,
       date(emitido_epoch, 'unixepoch')                       AS dia,
       source,
       COUNT(*)                                               AS total,
       SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END)         AS ok,
       SUM(CASE WHEN estado = 'RECHAZADO' THEN 1 ELSE 0 END)  AS rechazados,
       SUM(CASE WHEN estado = 'TIMEOUT' THEN 1 ELSE 0 END)    AS timeouts,
       ROUND(AVG(latencia_ms), 0)                             AS latencia_media_ms
  FROM commands
 GROUP BY device_id, dia, source;

-- Eventos que merecen atencion del operador
DROP VIEW IF EXISTS v_eventos_criticos;
CREATE VIEW v_eventos_criticos AS
SELECT id, device_id, ts_epoch, ts_utc, kind, severity, message, state
  FROM events
 WHERE severity IN ('warning', 'critical')
 ORDER BY ts_epoch DESC;

-- Ultimo estado de seguridad registrado por dispositivo
DROP VIEW IF EXISTS v_estado_actual;
CREATE VIEW v_estado_actual AS
SELECT s.device_id, s.hacia AS estado, s.ts_utc, s.motivo
  FROM state_changes s
  JOIN (SELECT device_id, MAX(ts_epoch) AS ultima
          FROM state_changes
         GROUP BY device_id) u
    ON u.device_id = s.device_id AND u.ultima = s.ts_epoch;
